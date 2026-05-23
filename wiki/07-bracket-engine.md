# Bracket Engine Guide

The Bracket Engine is responsible for generating and managing tournament bracket structures as directed graphs.

## Core Concepts

### Graph-Based Brackets

Tournament brackets are represented as directed graphs where:
- **Nodes** represent matches, groups, or final positions
- **Edges** represent progression paths (who advances where)
- **UUIDs** provide stable references for all operations

### Node Types

| Node Type | Description | Use Case |
|-----------|-------------|----------|
| `STANDARD` | Single elimination match | Winners bracket, losers bracket |
| `ROUND_ROBIN_GROUP` | Group with multiple matches | Group stages |
| `FINAL` | Championship match | Grand finals |
| `CONSOLATION` | Losers bracket match | Double elimination |
| `SWISS_ROUND` | Swiss system round | Swiss format tournaments |
| `GROUP_STAGE` | Generic group stage node | Multi-format tournaments |

---

## Bracket Generation Algorithms

### Single Elimination

```python
async def generate_single_elimination(
    self,
    tournament_id: UUID,
    team_count: int
) -> List[Node]:
    """Generate single elimination bracket."""
    nodes = []
    
    # Calculate rounds needed (power of 2)
    round_count = math.ceil(math.log2(team_count))
    
    # Create nodes for each round
    current_round_teams = team_count
    for round_num in range(round_count):
        matches_in_round = current_round_teams // 2
        
        for match_num in range(matches_in_round):
            node = Node(
                tournament_id=tournament_id,
                node_type=NodeType.STANDARD,
                stage_info={
                    "stage_number": round_num,
                    "description": f"Round {round_num + 1}"
                },
                next_nodes={}  # Will be connected later
            )
            nodes.append(node)
        
        current_round_teams = matches_in_round
    
    # Connect nodes (winner advances)
    self._connect_single_elim_nodes(nodes)
    
    return nodes
```

### Double Elimination

```python
async def generate_double_elimination(
    self,
    tournament_id: UUID,
    team_count: int
) -> List[Node]:
    """Generate double elimination bracket."""
    nodes = []
    
    # Calculate rounds
    winners_rounds = math.ceil(math.log2(team_count))
    losers_rounds = (winners_rounds - 1) * 2
    
    # Generate winners bracket
    winners_nodes = self._generate_winners_bracket(
        tournament_id, team_count, winners_rounds
    )
    nodes.extend(winners_nodes)
    
    # Generate losers bracket
    losers_nodes = self._generate_losers_bracket(
        tournament_id, winners_nodes, losers_rounds
    )
    nodes.extend(losers_nodes)
    
    # Generate grand final
    grand_final = self._create_grand_final(tournament_id)
    nodes.append(grand_final)
    
    # Connect all brackets
    self._connect_double_elim_nodes(winners_nodes, losers_nodes, grand_final)
    
    return nodes
```

### Round Robin Groups

```python
async def generate_round_robin_groups(
    self,
    tournament_id: UUID,
    teams: List[Team],
    groups_count: int,
    advance_per_group: int
) -> List[Node]:
    """Generate Round Robin group stage."""
    nodes = []
    
    # Distribute teams into groups
    groups = self._distribute_teams(teams, groups_count)
    
    # Create group nodes
    for group_idx, group_teams in enumerate(groups):
        group_letter = chr(ord('A') + group_idx)
        
        # Create group node
        group_node = Node(
            tournament_id=tournament_id,
            node_type=NodeType.ROUND_ROBIN_GROUP,
            stage_info={
                "group_letter": group_letter,
                "description": f"Group {group_letter}"
            },
            matches=[]
        )
        
        # Generate all matches within group (each team plays every other)
        group_matches = self._generate_round_robin_matches(
            tournament_id, group_teams, group_node.uuid
        )
        group_node.matches = [m.uuid for m in group_matches]
        
        nodes.append(group_node)
        
        # Create advancement nodes (semifinals, etc.)
        advancement_nodes = self._create_advancement_structure(
            tournament_id, group_letter, advance_per_group
        )
        
        # Set up next_nodes mapping
        group_node.next_nodes = {
            f"{i+1}st": adv_node.uuid 
            for i, adv_node in enumerate(advancement_nodes[:advance_per_group])
        }
        
        nodes.extend(advancement_nodes)
    
    return nodes
```

---

## Progression Logic

### Automatic Advancement

When a match is completed, the progression engine automatically advances winners:

```python
async def advance_winner(self, match: Match) -> None:
    """Advance winning team to next match."""
    if not match.winner_id:
        return  # No winner yet
    
    # Get parent node
    node = await self.node_repo.get_by_uuid(match.node_uuid)
    
    # Determine next position based on outcome
    next_node_uuid = node.next_nodes.get("winner")
    if not next_node_uuid:
        return  # Tournament complete
    
    next_node = await self.node_repo.get_by_uuid(next_node_uuid)
    
    # Find the match in next node that needs this team
    target_match = await self._find_open_match_slot(next_node)
    
    if target_match:
        # Assign winner to appropriate slot
        if not target_match.team_a_id:
            target_match.team_a_id = match.winner_id
        else:
            target_match.team_b_id = match.winner_id
        
        await self.match_repo.update(target_match)
        
        # Check if match can start (both teams assigned)
        if target_match.team_a_id and target_match.team_b_id:
            await self.websocket_manager.broadcast(
                node.tournament_id,
                "match.teams_assigned",
                {"match_uuid": str(target_match.uuid)}
            )
```

### Tiebreaker Handling

For Round Robin groups, standings determine advancement:

```python
async def calculate_group_standings(
    self,
    group_node: Node,
    matches: List[Match]
) -> List[TeamStanding]:
    """Calculate standings for Round Robin group."""
    standings = {}
    
    for match in matches:
        if match.status != MatchStatus.COMPLETED:
            continue
        
        # Update team A stats
        if match.winner_id == match.team_a_id:
            self._update_standing(standings, match.team_a_id, win=True)
            self._update_standing(standings, match.team_b_id, win=False)
        elif match.winner_id == match.team_b_id:
            self._update_standing(standings, match.team_b_id, win=True)
            self._update_standing(standings, match.team_a_id, win=False)
        else:
            # Draw
            self._update_standing(standings, match.team_a_id, draw=True)
            self._update_standing(standings, match.team_b_id, draw=True)
    
    # Sort by points, then tiebreakers
    sorted_standings = sorted(
        standings.values(),
        key=lambda s: (s.points, s.tiebreaker_1, s.tiebreaker_2),
        reverse=True
    )
    
    return sorted_standings
```

---

## Manual Bracket Adjustments

Organizers may need to manually adjust brackets:

### Reassign Teams

```python
async def manual_team_assignment(
    self,
    match_uuid: UUID,
    team_a_id: Optional[UUID],
    team_b_id: Optional[UUID],
    actor_id: UUID
) -> Match:
    """Manually assign teams to a match."""
    match = await self.match_repo.get_by_uuid(match_uuid)
    
    old_state = match.dict()
    
    match.team_a_id = team_a_id
    match.team_b_id = team_b_id
    
    await self.match_repo.update(match)
    
    # Log audit event
    await self.audit_service.log_change(
        entity_type="match",
        entity_id=str(match_uuid),
        action="manual_assignment",
        before=old_state,
        after=match.dict(),
        actor_id=actor_id
    )
    
    return match
```

### Modify Progression Paths

```python
async def update_progression(
    self,
    node_uuid: UUID,
    new_next_nodes: dict,
    actor_id: UUID
) -> Node:
    """Manually update node progression paths."""
    node = await self.node_repo.get_by_uuid(node_uuid)
    
    old_next_nodes = node.next_nodes.copy()
    
    # Validate that referenced nodes exist
    for outcome, next_uuid in new_next_nodes.items():
        if next_uuid and not await self.node_repo.exists(next_uuid):
            raise ValueError(f"Next node {next_uuid} does not exist")
    
    node.next_nodes = new_next_nodes
    
    await self.node_repo.update(node)
    
    # Log audit event
    await self.audit_service.log_change(
        entity_type="node",
        entity_id=str(node_uuid),
        action="progression_updated",
        before={"next_nodes": old_next_nodes},
        after={"next_nodes": new_next_nodes},
        actor_id=actor_id
    )
    
    return node
```

---

## Overlay Configuration

Nodes can include hints for external overlay software:

```json
{
  "uuid": "uuid-node",
  "overlay_config": {
    "position": "top_left",
    "label": "Winners Final",
    "priority": 1,
    "display_order": 5,
    "color_scheme": "gold",
    "show_timer": true,
    "best_of": 3
  }
}
```

Overlay directors use this data to configure their rendering software.

---

## Common Patterns

### BYE Handling

When team count isn't a power of 2:

```python
def handle_byes(self, teams: List[Team], bracket_size: int) -> List[Tuple[Optional[Team], Optional[Team]]]:
    """Create first round matchups with BYEs."""
    bye_count = bracket_size - len(teams)
    
    # Seed teams and add BYEs
    seeded_teams = self.seed_teams(teams)
    matchups = []
    
    for i in range(bracket_size // 2):
        team_a = seeded_teams[i] if i < len(seeded_teams) else None
        team_b = seeded_teams[bracket_size - 1 - i] if (bracket_size - 1 - i) < len(seeded_teams) else None
        
        # Auto-advance if BYE
        if team_a and not team_b:
            # Team A gets BYE, auto-advance
            self.auto_advance(team_a)
        elif team_b and not team_a:
            # Team B gets BYE, auto-advance
            self.auto_advance(team_b)
        
        matchups.append((team_a, team_b))
    
    return matchups
```

### Grand Final Reset

For double elimination with bracket reset:

```python
async def check_grand_final_reset(self, grand_final: Match) -> bool:
    """Check if grand final needs reset (losers bracket winner wins first series)."""
    if grand_final.status != MatchStatus.COMPLETED:
        return False
    
    # Check if losers bracket team won
    losers_team = await self.get_losers_bracket_representative()
    
    if grand_final.winner_id == losers_team.id:
        # Create second grand final match
        reset_match = await self.create_grand_final_reset(grand_final)
        
        await self.websocket_manager.broadcast(
            grand_final.tournament_id,
            "bracket.grand_final_reset",
            {"new_match_uuid": str(reset_match.uuid)}
        )
        
        return True
    
    return False
```

---

## Performance Considerations

### Batch Operations

```python
# Good: Batch insert all nodes
async def create_bracket_batch(self, nodes: List[Node]):
    async with self.db.begin():
        self.db.add_all(nodes)
        await self.db.flush()

# Bad: Individual inserts
async def create_bracket_individual(self, nodes: List[Node]):
    for node in nodes:  # ❌ Slow!
        self.db.add(node)
        await self.db.commit()
```

### Eager Loading

```python
# Load complete bracket efficiently
async def get_full_bracket(self, tournament_id: UUID):
    result = await self.session.execute(
        select(Tournament)
        .options(
            selectinload(Tournament.nodes)
                .selectinload(Node.matches)
                .selectinload(Match.team_a),
            selectinload(Tournament.nodes)
                .selectinload(Node.matches)
                .selectinload(Match.team_b)
        )
        .where(Tournament.id == tournament_id)
    )
    return result.scalar_one_or_none()
```

---

## Testing Bracket Generation

```python
@pytest.mark.asyncio
async def test_double_elim_generation(bracket_engine: BracketEngine):
    """Test double elimination bracket generation."""
    # Arrange
    tournament_id = uuid4()
    team_count = 8
    
    # Act
    nodes = await bracket_engine.generate_double_elimination(
        tournament_id, team_count
    )
    
    # Assert
    assert len(nodes) > 0
    
    # Verify structure
    winners_nodes = [n for n in nodes if n.stage_info["bracket"] == "winners"]
    losers_nodes = [n for n in nodes if n.stage_info["bracket"] == "losers"]
    
    assert len(winners_nodes) == 7  # 4 + 2 + 1
    assert len(losers_nodes) == 6   # Appropriate losers bracket size
    
    # Verify connections
    for node in nodes:
        if node.node_type == NodeType.STANDARD:
            assert "winner" in node.next_nodes or node.is_final()
```

---

## Next Steps

Continue reading:
- [Authentication & Authorization](./08-authentication.md) - Managing access control
- [Audit Trail](./09-audit-trail.md) - Tracking all changes
