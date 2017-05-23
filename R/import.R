library(readr)
library(data.table)
library(ggplot2)

col_types_PB <- cols(
  popular_vote_percent = col_number(), seats = col_integer()
)
col_types_RE <- cols(
  total_valid_vote = col_integer(),
  voter_turnout = col_integer(),
  voter_turnout_percent = col_number(),
  rejected_ballot = col_integer(),
  rejected_ballot_percent = col_number(),
  expense_limit = col_number(),
  is_by_election = col_logical()
)
col_types_PE <- cols(
  candidates = col_integer(),
  popular_vote = col_integer(),
  popular_vote_percent = col_number(),
  popular_vote_delta_percent = col_number(),
  seats_dissolution = col_number(),
  seats_elected = col_number()
)
col_types_CRE <- cols(
  order = col_integer(),
  votes = col_integer(),
  votes_percent = col_number(),
  delta_percent = col_number(),
  elected = col_logical()
)
P <- data.table(read_csv("Party.csv"))
PB <- read_csv("ProvincialBreakdown.csv", col_types=col_types_PB)
RE <- data.table(read_csv("RidingElection.csv", col_types=col_types_RE))
PE <- data.table(read_csv("PartyElection.csv", col_types=col_types_PE))
CRE <- data.table(read_csv("CandidateRidingElection.csv", col_types=col_types_CRE))

PECRE <- PE[P[CRE[RE, on=c("re_id")], on=c("party_name")], on=c("party_name","election_id")]
PECRE[,party_name := ifelse(party_name == "New Democratic Party", "New Democratic", party_name)]
PECRE[,leader := ifelse(leader == "Tom Mulcair", "Thomas Mulcair", leader)]

PECRE <- PECRE[order(election_id,decreasing=TRUE)]
setkey(PECRE,riding_id,candidate_name,election_id)
PECRE <- PECRE[,incumbency:=as.integer(1:.N),by=c("riding_id","candidate_name")]

PECRE[,is_leader := candidate_name == leader]

scale_party_colours <- scale_color_manual(values=setNames(P$colour, P$party_name))
scale_party_fills <- scale_fill_manual(values=setNames(P$colour, P$party_name))
