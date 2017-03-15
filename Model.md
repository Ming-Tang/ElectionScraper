# `Party`

 - `party_name`
 - `kind`: `provincial`/`federal`
 - `short_name`
 - `colour`


# `Riding`

 - `riding_name`
 - `province`

# `Election`

 - `eid`: Unique identifier of this election: province + year for provincial and year for federal
 - `prev_eid`: Unique identifier of the previous election.
 - `number`
 - `kind`: `provincial`/`federal`
 - `province`: Province of the provincial election.
 - `year`
 - `date`
 - `voter_turnout`
 - `total_seats`: Number of seats contested.
 - `majority_seats`: Number of seats required for majority.
 - `party1`
 - `party2`
 - `party3`
 - `party4`
 - `party5`
 - `leader_elected`: Full name of the party leader elected.

# `RidingElection`

 - `riding_name`: Full name of the riding.

# `PartyElection`

 - `party_name`
 - `eid`
 - `candidates`: Number of candidates fielded.
 - `complete`: True if party is present in all ridings.
 - `leader`: Full name of party leader.
 - `position`
 - `seats_before`
 - `seats_won`
 - `seat_percent`
 - `popular_vote_before`
 - `popular_vote`
 - `popular_vote_where_running`

# `Candidate`

A candidate is identifier by `full_name` and `kind`.

 - `full_name`: Full name of the candidate.
 - `kind`: `provincial`/`federal`.

# `PartyLeadership`

 - `full_name`
 - `party_name`
 - `kind`: `provincial`/`federal`
 - `start_year`
 - `end_year`

# `Poll`

 - `poll_id`:
 - `date`
 - `polling_firm`
 - `link`
 - `margin_of_error`
 - `sample_size`
 - `polling_method`
 - `lead`

# `RegionalPoll`

 - `poll_id`
 - `region_name`

# `PollItem`

 - `poll_id`
 - `party_name`
 - `kind`: `provincial`/`federal`
 - `percentage`
 - `count`

# `Province`

 - `province`: Short name of province.
 - `population`
 - `population_year`
 - `lat`
 - `lon`

# `Region`

 - `region_name`
 - `province`
 - `lat`
 - `lon`
 - `population`
 - `population_year`
