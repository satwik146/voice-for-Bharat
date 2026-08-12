from livekit.agents import AgentSession
import inspect

print("Methods in AgentSession:")
methods = [m[0] for m in inspect.getmembers(AgentSession)]
if "say" in methods:
    print("YES, AgentSession has say()")
else:
    print("NO, AgentSession does NOT have say()")
