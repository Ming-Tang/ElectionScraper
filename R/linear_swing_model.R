#data <- PECRE[riding_id == "Toronto-Danforth" & election_id>"F1960"]
data <- PECRE[election_id>"F1990"]
data1 <- data[,.(
  election_id, party_name,
  votes_percent, popular_vote_percent,
  popular_vote_delta_percent, delta_percent)];
cons <- c("Conservative","Progressive Conservative")
data1[, `:=`(
  LIB=.SD[party_name=="Liberal"]$votes_percent,
  CON=.SD[party_name %in% cons]$votes_percent,
  NDP=.SD[party_name=="New Democratic"]$votes_percent,
  BQ=.SD[party_name=="Bloc Québécois"]$votes_percent,
  GRN=.SD[party_name=="Green"]$votes_percent,
  
  PV.LIB=.SD[party_name=="Liberal"]$popular_vote_percent,
  PV.CON=.SD[party_name %in% cons]$popular_vote_percent,
  PV.NDP=.SD[party_name=="New Democratic"]$popular_vote_percent,
  PV.BQ=.SD[party_name=="Bloc Québécois"]$popular_vote_percent,
  PV.GRN=.SD[party_name=="Green"]$popular_vote_percent,
  
  dLIB=.SD[party_name=="Liberal"]$delta_percent,
  dCON=.SD[party_name %in% cons]$delta_percent,
  dNDP=.SD[party_name=="New Democratic"]$delta_percent,
  dPV.LIB=.SD[party_name=="Liberal"]$popular_vote_delta_percent,
  dPV.CON=.SD[party_name %in% cons]$popular_vote_delta_percent,
  dPV.NDP=.SD[party_name=="New Democratic"]$popular_vote_delta_percent
  ), by="election_id"]
data1 <- data1[, .SD[1], by="election_id"][,
  .(election_id,
    LIB, CON, NDP, BQ, GRN,
    PV.LIB, PV.CON, PV.NDP, PV.BQ, PV.GRN,
    dLIB, dCON, dNDP,
    dPV.LIB, dPV.CON, dPV.NDP)]
View(data1)

model <- lm(LIB ~ PV.LIB, data=data1); summary(model); sum(model$residuals**2)
model <- lm(CON ~ PV.CON, data=data1); summary(model); sum(model$residuals**2)
model <- lm(NDP ~ PV.NDP, data=data1); summary(model); sum(model$residuals**2)
model <- lm(LIB ~ PV.LIB + PV.CON + PV.NDP, data=data1); summary(model); sum(model$residuals**2)
model <- lm(CON ~ PV.LIB + PV.CON + PV.NDP, data=data1); summary(model); sum(model$residuals**2)
model <- lm(NDP ~ PV.LIB + PV.CON + PV.NDP, data=data1); summary(model); sum(model$residuals**2)

library(corrplot)
corM <- cor(data1[,.(LIB,CON,NDP,BQ,GRN,PV.LIB,PV.CON,PV.NDP,PV.BQ,PV.GRN)], use="complete")
corrplot(corM, method="number")
