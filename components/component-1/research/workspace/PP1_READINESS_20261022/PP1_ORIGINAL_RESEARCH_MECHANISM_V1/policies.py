"""Finite-state review policies. No hidden outcome or GT is accepted by selectors."""
import itertools,functools
STATES=list(itertools.product([0,1],repeat=3))
def posterior(observed):return [i for i,s in enumerate(STATES) if all(s[k]==v for k,v in observed.items())]
def terminal(loss,indices):
 vals=[sum(loss[i][d] for i in indices)/len(indices) for d in range(len(loss[0]))]
 j=min(range(len(vals)),key=lambda d:(vals[d],d));return vals[j],j

def proposed(loss,observed,budget):
 """Partition-recursive Bayes risk; standard finite-horizon VOI, not new theory."""
 @functools.lru_cache(None)
 def solve(obs,b):
  ob=dict(obs);ids=posterior(ob);value,decision=terminal(loss,ids);action=None
  if b:
   for k in range(3):
    if k in ob:continue
    score=0.
    for v in [0,1]:
     nxt=tuple(sorted([*obs,(k,v)]));subset=posterior(dict(nxt))
     if subset:score+=len(subset)/len(ids)*solve(nxt,b-1)[0]
    if score<value-1e-12:value=score;action=k
  return value,action,decision
 return solve(tuple(sorted(observed.items())),budget)

def conventional_task_aware(loss,observed,budget):
 """Independent belief-state Bellman implementation, same info/stop/tie policy."""
 def bellman(belief,known,remaining):
  values=[]
  for decision in range(len(loss[0])):
   values.append(sum(loss[state][decision] for state in belief)/len(belief))
  decision=min(range(len(values)),key=lambda x:(values[x],x));best=values[decision];query=None
  if remaining>0:
   for feature in sorted(set(range(3))-set(known)):
    branches=[[s for s in belief if STATES[s][feature]==label] for label in (0,1)]
    expected=sum(len(branch)*bellman(branch,known|{feature},remaining-1)[0] for branch in branches if branch)/len(belief)
    if expected<best-1e-12:best=expected;query=feature
  return best,query,decision
 return bellman(posterior(observed),set(observed),budget)

def greedy_voi(loss,observed,budget):
 ids=posterior(observed);value,decision=terminal(loss,ids);action=None
 if budget:
  for k in sorted(set(range(3))-set(observed)):
   parts=[[i for i in ids if STATES[i][k]==v] for v in (0,1)]
   risk=sum(len(p)*terminal(loss,p)[0] for p in parts if p)/len(ids)
   if risk<value-1e-12:value=risk;action=k
 return value,action,decision

def replay(method,loss,truth,budget,order=None):
 observed={};trace=[];remaining=budget
 while True:
  if method in ['NEW','NO_AUTHORITY']:risk,action,decision=proposed(loss,observed,remaining)
  elif method=='B5':risk,action,decision=conventional_task_aware(loss,observed,remaining)
  elif method=='B3':risk,action,decision=greedy_voi(loss,observed,remaining)
  else:
   risk,decision=terminal(loss,posterior(observed));action=next((k for k in order if k not in observed),None) if remaining else None
  if action is None:break
  answer=truth[action] # Simulated reviewer: selector never receives this truth.
  trace.append(dict(fact=action,answer=answer,predicted_remaining_risk=risk));observed[action]=answer;remaining-=1
 return dict(decision=decision,observed=observed,trace=trace,review_cost=len(observed),posterior=posterior(observed),conditional_expected_loss=terminal(loss,posterior(observed))[0])
