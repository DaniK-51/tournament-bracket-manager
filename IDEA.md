# Key idea
Backed application that manages tournaments. It saves tournament bracket and list of teams. It'll be used to structure judge and overlay director workflow
Service will be used by overlay apps via api
Goal is to create universal service, that handle all overlay apps (for cyber sport, IRL sport, etc.)

# Tournament storage structure
Tournament entity has a bracket, name, discipline and ID (6 digit number)
Bracket represented as a directed graph. Information about edges stores inside nodes. For e.g. stage match has reference to next node for winner and reference to next node for loser, group has reference to next node for every position in internal leader board. Node can represent stage match, Round Robin group or final position in tournament. 
Nodes has matches inside (1 for stage mach, multiple for group).
Each Node and Match has uuid that used as reference to element

# Endpoints
PUT /tournament/{ID}
PUT /match/{UUID} or /tournament/{ID}/match/{UUID}
PUT /node/{UUID} or /tournament/{ID}/node/{UUID}

POST /tournament/{ID}/match/new
POST /tournament/{ID}/node/new
POST /tournament/new

GET /tournament/{ID}
GET /match/{UUID} or /tournament/{ID}/match/{UUID}
GET /node/{UUID} or /tournament/{ID}/node/{UUID}

DELETE /tournament/{ID}
DELETE /match/{UUID} or /tournament/{ID}/match/{UUID}
DELETE /node/{UUID} or /tournament/{ID}/node/{UUID}

# Metadata
All data (exept for uuid, created_at, etc.) for matches, nodes and teams stores in jsonb
