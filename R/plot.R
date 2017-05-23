setwd("~/Code/ElectionScraper/output")
source("import.R")

ridings <- c(
  "Central Nova",
  "Halifax West",
  "Saanich-Gulf Islands",
  "Vancouver Quadra",
  "Victoria",
  "New Westminster-Coquitlam",
  "Burnaby-New Westminster",
  "Skeena",
  "Toronto Centre",
  "Toronto-Danforth",
  "Ottawa-Vanier",
  "Outremont",
  "Papineau",
  "Crowfoot",
  "Calgary Southwest",
  "Laurier-Sainte-Marie",
  "Québec",
  "Wild Rose",
  "Halifax West",
  "Winnipeg Centre",
  "Yukon"
)
parties = c(
  "Liberal", "Conservative", "Green", "New Democratic",
  "Bloc Québécois"
  #"Progressive Conservative"
  #"Reform"
)
data <- PECRE
data <- data[election_id > "F1930"]
slopes <- data[, tryCatch({
  model <- lm(votes_percent ~ popular_vote_percent, data=.SD, na.action=na.exclude, singular.ok=TRUE)
  .(n=.N, slope=coef(model)["popular_vote_percent"], intercept=coef(model)["(Intercept)"])
}, error=function(e) { .(n=.N, slope=NA_real_, intercept=NA_real_) }), by=.(party_name,riding_id)]

#ridings <- sample(RE$riding_id, 50)
#ridings <- PECRE[election_id>"F2000",]$riding_id

data <- data[
  #votes_percent <= 100 & popular_vote_percent > 3 &
  riding_id %in% ridings &
  party_name %in% parties
]

setorder(data, -election_id)

plt <- ggplot(aes(
  x=popular_vote_percent, y=votes_percent,
  #x=popular_vote_delta_percent, y=delta_percent/popular_vote_delta_percent,
  group=party_name,
  col=party_name,
  #shape=is_leader,
  #label=paste(sub("F20", "''", sub("F19", "", election_id)), ifelse(elected,"E",""),sep=""),
  label=sub("F20", "''", sub("F19", "", election_id)),
  alpha=incumbency),
  data=data)
plt +
  #geom_abline(slope=1,intercept=1,col="white") +
  geom_smooth(method="lm", se=FALSE, alpha=0.3) +
  #geom_point(aes(size=incumbency, shape=is_leader), data=data[elected == TRUE], fill="transparent", stroke=2, col="black", alpha=0.4) +
  geom_point(aes(size=incumbency, shape=elected)) +
  scale_size_continuous(range = c(3, 6)) +
  scale_shape_manual(values = c(19, 15)) +
  geom_text(col="white", size=1.7) +
  geom_text(aes(label=leader), data=data[TRUE == is_leader],
            size=3, hjust="inward", vjust=-1, nudge_x=2, nudge_y=1) +
  geom_path(alpha=0.25, na.rm = TRUE) +
  scale_alpha_continuous(range = c(0.8, 1)) +
  scale_party_colours +
  #facet_grid(party_name ~ riding_id) +
  facet_wrap(~riding_id) +
  scale_x_continuous(breaks=seq(0,100,10),minor_breaks=seq(0,100,5),limits=c(0,50)) +
  scale_y_continuous(breaks=seq(0,100,10),minor_breaks=seq(0,100,5),limits=c(0,100)) +
  #scale_x_continuous(breaks=seq(-20,20,10),minor_breaks=seq(-20,20,5)) + xlim(-20,20) +
  #scale_y_continuous(breaks=seq(-50,50,10),minor_breaks=seq(-50,50,5)) + ylim(-20,20) +
  theme(legend.position="right")

n0 <- 3
slopes_summary <- slopes[
  n > n0 & party_name %in% parties,
  .(mean=mean(slope,na.rm=TRUE),
    median=median(slope,na.rm=TRUE),
    sd=sd(slope,na.rm=TRUE),
    min=min(slope,na.rm=TRUE),
    max=max(slope,na.rm=TRUE)),
  by=party_name][mean>0.01,][order(mean),]

intercepts_summary <- slopes[
  n > n0 & party_name %in% parties & -120 < intercept & intercept < 120,
  .(mean=mean(intercept,na.rm=TRUE),
    median=median(intercept,na.rm=TRUE),
    sd=sd(intercept,na.rm=TRUE),
    min=min(intercept,na.rm=TRUE),
    max=max(intercept,na.rm=TRUE)),
  by=party_name][mean>0.01,][order(mean),]
slopes_summary
intercepts_summary