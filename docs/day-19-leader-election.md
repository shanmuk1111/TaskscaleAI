# Day 19 – Leader Election

## Objective

Implement leader election so that multiple scheduler instances can coordinate and only one scheduler acts as the active leader at a time.

Redis is used as the shared coordination mechanism.

---

## What Was Implemented

A new leader election module was created:

app/leader_election.py



The leader is stored using the Redis key:

taskscale:scheduler_leader

The leadership lease has a timeout of:

10 seconds


## Leader Election

A scheduler attempts to become leader using a Redis SET operation with the NX option.

Only the scheduler that successfully creates the leader key becomes leader.

Other schedulers remain followers.

The system therefore supports:

Scheduler 1 → LEADER
Scheduler 2 → FOLLOWER
Scheduler 3 → FOLLOWER

## Leadership Renewal

A leader can renew its leadership lease using:

renew_leadership(leader_id)

The renewal resets the Redis key expiration.

Testing showed:

Renew 1: True
Renew 2: True
Renew 3: True
TTL: 10

This confirms that a healthy leader can maintain its leadership.

## Scheduler Integration

The scheduler now follows this flow:
            
            Multiple Schedulers
                    ↓
            Leader Election
                    ↓
            One Scheduler Becomes Leader
                    ↓
            Renew Leadership
                    ↓
            Distributed Lock
                    ↓
            Priority Queue
                    ↓
            Redis Stream
                    ↓
            Workers

A scheduler that is not the leader waits instead of processing the priority queue.

## Testing

### Test 1 – Single Leader

The first scheduler successfully became leader:

This scheduler is now LEADER: <UUID>

A second scheduler reported:

Another scheduler is currently LEADER

This confirmed that only one scheduler becomes leader.

### Test 2 – Leadership Renewal

The leader successfully renewed its lease multiple times:

Renew 1: True
Renew 2: True
Renew 3: True

The Redis TTL was restored to approximately:

10 seconds

### Test 3 – Leader Failover

Two scheduler instances were started.

The first scheduler became leader.

The second scheduler initially reported:

Another scheduler is currently LEADER

The first scheduler was then stopped.

The second scheduler subsequently became leader:

This scheduler is now LEADER: ce4e9b4d-...

This confirmed that leadership can transfer between scheduler instances.

## Result

TaskScale AI now supports Redis-based leader election and scheduler failover.

Only one scheduler acts as leader at a time, while another scheduler can take over when the current leader stops.

## Status

Day 19 – COMPLETE ✅