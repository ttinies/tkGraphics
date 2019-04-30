
from sc2gameLobby import versions as v
from sc2gameLobby.gameConfig import Config


h = v.handle

recent = h.mostRecent
print(recent)
print(h.search())
#print(v.Version(recent))
print()

cfg = Config()
print(cfg.getVersion())
