# Key idea
Backed application that manages tournaments. It saves tournament bracket and list of teams. It'll be used to structure judge and overlay director workflow  

# Tournament storage structure
Tournament entity has a bracket, name and ID (6 digit number)
Bracket represented as a directed graph. Information about edges stores inside nodes. For e.g. stage match has reference to next match for winner and reference to next match for loser, group has reference to next match for every position in internal leader board. Node can represent stage match, Round Robin group or final position in tournament. Nodes has matches inside (1 for stage mach, multiple for group).
Each node has uuid that used as reference to element. Matches has uuid to

# Endpoints
POST /{ID}/add
PUT /{ID}/{UUID}
POST /new/{ID}
GET /{ID}
GET /{UUID}
