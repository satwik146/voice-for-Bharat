# Day 5 – The Tools

Yesterday your agent learned to remember things you said. Today, you will teach it how to learn off the internet.

For Day 5, your objective is to build at least one function call that fetches or computes real domain data for your track.

- **Step 1: Pick the one lookup your agent can't do its job without.** 

  Examples of what your track's tools could be:

  | Track | Tool |
  |---|---|
  | Farm & Field | Market price lookup by crop and location; weather forecast by district |
  | Health Access | Symptom-to-triage-level classifier; nearest PHC or facility lookup |
  | Learning & Literacy | Fetch next exercise by level; score a spoken answer |
  | Local Commerce | Catalogue and stock lookup; compute an order total |
  | Financial Services | Scheme eligibility check from collected answers; document checklist |
  | Disaster Response | Alert status by district; nearest shelter and capacity |

- **Step 2: Use real data if you can reach it.** A government API, a public dataset, a scraped CSV, an open weather API. If nothing is available, a hand-built local dataset is acceptable, but say so in your README.

- **Step 3: Write the tool description carefully.** The model decides when to call it based on that description alone. If it fires at the wrong time or never fires, your description is the bug.

- **Step 4: Handle the failure path out loud.** APIs time out, especially on the connections your users have. The agent must say something useful instead of going silent or inventing an answer. 

- **Step 5: Say when the data is from.** "Yesterday's rate" and "today's rate" are different decisions for the person listening.

- **Step 6: Successfully connect to your agent** and ask it something that requires the tool.

- **Step 7: Record a short video** showing the tool firing on a real question and, if you can, the graceful failure when the data source is down.

- **Step 8: Post the video on LinkedIn** with a description of what you built on Day 5. Mention that you're building a voice agent using the fastest TTS API — **Murf Falcon**. Mention that you're part of **10 Days of Voice Agents** and don't forget to tag the official **Murf AI** handle. Also use the hashtag **#VoiceForBharat**.

- **Step 9: Submit your post link on the form given on Discord.** 

## Advanced (Optional)

You only need the steps above to complete Day 5. These are for going the extra mile:

- **Chain two tools.** Look up the user's district from Day 4, then use it in today's lookup without asking again.
- **Push results to the UI.** Show the fetched data on screen while the agent speaks it. Prices and shelter addresses are hard to hold in your head.
- **Connect an MCP server** instead of hand-rolling an integration. See the [Model Context Protocol intro](https://modelcontextprotocol.io/docs/getting-started/intro).

### You've finished Day 5 if:

- The agent calls your tool at the right moment without being told to
- Returned data is spoken naturally, not read out as JSON
- Killing the data source produces a graceful spoken fallback, not silence or a hallucination
- Your README says whether the data is live or local

Once your agent is running, your LinkedIn post is live and your form submission is in, you've completed Day 5.

## Resources

- [Tool Definition and Use](https://docs.livekit.io/agents/logic/tools/)
- [MCP Integration](https://docs.livekit.io/agents/logic/tools/mcp/)
- [Drive-thru Agent Example](https://github.com/livekit/agents/blob/main/examples/drive-thru/agent.py)