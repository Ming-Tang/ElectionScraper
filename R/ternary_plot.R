library(ggtern)

#cur_election <- "F2011"
#prev_election <- "F2008"
cur_election <- "F2015"
prev_election <- "F2011"

parties <- c("Liberal", "Conservative", "Green", "New Democratic", "Bloc Québécois")

by_party <- function(.SD, key, func=NA) {
  if (!is.function(func)) func <- function(x) x
  list(
    LIB=func(.SD[party_name=="Liberal"][[key]]),
    CON=func(.SD[party_name=="Conservative"][[key]]),
    NDP=func(.SD[party_name=="New Democratic"][[key]]),
    GRN=func(.SD[party_name=="Green"][[key]]),
    BQ=func(.SD[party_name=="Bloc Québécois"][[key]]))
}

data1 <- PECRE[prev_election == election_id | election_id == cur_election][party_name %in% parties][
  ,c(by_party(.SD, "votes_percent"),
     .(winner=.SD[elected == TRUE]$party_name,
       margin=.SD[order==0]$votes_percent - .SD[order==1]$votes_percent,
       leader=if(any(.SD$is_leader)) { .SD[is_leader == TRUE,]$candidate_name[1] } else { "" },
       leader_party=if(any(.SD$is_leader)) { .SD[is_leader == TRUE,]$party_name[1] } else { "" },
       leader_lost=if(any(.SD$is_leader)) { .SD[is_leader == TRUE,][1]$order != 0 } else { NA })),
  by=c("election_id","riding_id")][order(election_id)]

data_pv <-  PECRE[prev_election == election_id | election_id == cur_election][party_name %in% parties][
  , by_party(.SD, "popular_vote_percent", func=function(x) x[1])
  #.(LIB=.SD[party_name=="Liberal"]$popular_vote_percent[1],
  #   CON=.SD[party_name=="Conservative"]$popular_vote_percent[1],
  #   NDP=.SD[party_name=="New Democratic"]$popular_vote_percent[1],
  #   GRN=.SD[party_name=="Green"]$popular_vote_percent[1],
  #   BQ=.SD[party_name=="Bloc Québécois"]$popular_vote_percent[1])
  , by="election_id"]
data_pv[,`:=`(
  winner=parties[order(LIB, CON, GRN, NDP, BQ)[1]],
  riding_id=NA
)]

data1[, leader := ifelse(leader_lost == TRUE, paste(leader, "(lost)"), leader)]

opts <- list(
  geom_path(alpha=0.6, arrow=arrow(angle=25, length=unit(0.3, "cm"), type="closed"), na.rm=TRUE),
  geom_point(aes(size=margin), alpha=0.65, na.rm=TRUE),
  scale_size(range = c(2, 5)),
  geom_path(data=data_pv, alpha=1, size=0.8,
            arrow=arrow(angle=30, length=unit(0.2, "cm"), type="closed"),
            col="black", na.rm=TRUE),
  scale_party_colours,
  geom_text(aes(label=leader), na.rm=TRUE, col="black", size=3, hjust="inward", vjust="inward"), #(, size=3, hjust="inward", vjust=-1, nudge_x=2, nudge_y=1),
  scale_alpha_continuous(range=c(0.4, 1))
  #, scale_shape_manual(values = c(19, 15))
)

ggtern(data=data1, aes(x=LIB, y=NDP, z=CON, col=winner, group=riding_id)) + opts
ggtern(data=data1, aes(y=GRN, x=CON, z=NDP, col=winner, group=riding_id)) + opts
ggtern(data=data1, aes(y=GRN, x=LIB, z=NDP, col=winner, group=riding_id)) + opts
ggtern(data=data1, aes(y=GRN, x=LIB, z=CON, col=winner, group=riding_id)) + opts
ggtern(data=data1, aes(x=LIB, y=BQ, z=NDP, col=winner, group=riding_id)) + opts
ggtern(data=data1, aes(x=CON, y=BQ, z=NDP, col=winner, group=riding_id)) + opts
ggtern(data=data1, aes(x=LIB, y=BQ, z=CON, col=winner, group=riding_id)) + opts

opts1 <- list(
  geom_path(alpha=0.6, arrow=arrow(angle=25, length=unit(0.2, "cm"), type="closed"), na.rm=TRUE),
  geom_point(na.rm=TRUE),
  scale_party_colours,
  facet_wrap(~riding_id),
  theme(legend.position="none")
)

setorder(PECRE, election_id, riding_id)
data1 <- PECRE[election_id>="F1990"][
  ,c(by_party(.SD, "votes_percent"), .(winner=.SD[elected==TRUE]$party_name)),
  by=c("election_id","riding_id")]
keeps <- data1[,.(keep=.N>1),by="riding_id"][keep==TRUE,]$riding_id
keeps <- sample(keeps, 10)
data1 <- data1[riding_id %in% keeps]
data_pv <- PECRE[election_id>="F1990"][riding_id %in% keeps][
  , by_party(.SD, "popular_vote_percent"), by=c("election_id","riding_id")]
ggtern(data=data1, aes(x=LIB, y=NDP, z=CON, col=winner, group=riding_id)) +
  opts1 +
  geom_path(
    data=data_pv, na.rm=TRUE, alpha=1, size=0.8,
    arrow=arrow(angle=30, length=unit(0.2, "cm"), type="closed"), col="black")
