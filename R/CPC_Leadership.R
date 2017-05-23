library(readr)
library(data.table)
library(ggplot2)

CPCLeadership <- data.table(read_csv("~/Desktop/CPCLeadership.csv"))
CPCLeadership <- CPCLeadership[order(-votes_percent)][,c(.SD,.(order=1:.N)),by="riding"]
setorder(CPCLeadership, riding, name)

Winners <- CPCLeadership[, .SD[order(-votes_percent)][1], by="riding"]
Winners <- Winners[,c(.SD, .(X=as.integer(floor(lon*3)), Y=as.integer(floor(lat*3))))]
Zooms <- Winners[,.N,by=c("X","Y")][N>3][order(-N)][, id := 1:.N]
setkey(Zooms, id)

CPC_PV <- CPCLeadership[, .(popular_vote=sum(votes_percent)/.N), by="name"]

Elected2015 <- PECRE[election_id=="F2015" & elected==TRUE, .(riding=riding_id,elected_party=party_name,elected_votes_percent=votes_percent)]
Results2015 <- PECRE[election_id=="F2015", .(riding=riding_id,party_name=party_name,votes_percent2015=votes_percent,order2015=order+1,elected=elected)]

F2015_PV <- Results2015[, .(popular_vote=sum(votes_percent2015)/.N), by="party_name"][popular_vote>2]

Combined <- CPCLeadership[Results2015, on="riding", allow.cartesian=TRUE][party_name %in% F2015_PV$party_name]
Combined <- F2015_PV[,.(party_name=party_name, popular_vote2015=popular_vote)][CPC_PV[Combined,on="name"],on="party_name"]
setorder(Combined, riding, name, party_name)

Winners <- Elected2015[Winners, on="riding"]
Winners[,Group:={x<-X;y<-Y;Zooms[X==x & Y==y]$id},by=c("X","Y")]

setorder(Winners, lat)
Winners[,olat:=1:.N]
setorder(Winners,lon)
Winners[,olon:=1:.N]

setorder(Winners, olon, olat)
Winners[,olat1:=1:.N,by="olon"]
setorder(Winners, olon, olat1)

ggplot(aes(x=olon, y=olat, label=interaction(riding, name)), data=Winners[!is.na(Group)]) + geom_text() + facet_wrap(~Group, scales = "free")
ggplot(aes(x=olon, y=olat, label=interaction(riding, name)), data=Winners[is.na(Group)]) + geom_text()

ggplot(aes(x=lon, y=lat, shape=name), data=Winners[!is.na(Group)]) + geom_point() + facet_wrap(~Group, scales = "free")
ggplot(aes(x=lon, y=lat, shape=name), data=Winners[is.na(Group)]) + geom_point()


CPCLeadership <- Elected2015[CPCLeadership, on="riding"]

Counts <- Winners[,.N, by=c("elected_party","name")]
ggplot(aes(x=lon, y=lat, label=interaction(name, elected_party), size=votes_percent), data=Winners) + geom_text()
ggplot(aes(x=votes_percent, y=elected_votes_percent), data=Winners) + geom_point() + facet_grid(name ~ elected_party)
qplot(votes_percent2015,votes_percent,data=Combined[!is.na(interaction(name,party_name))], col=party_name, alpha=I(0.5), geom="density_2d") +
  geom_point() + scale_party_colours + facet_grid(party_name~name) + geom_rug() + geom_smooth(method="lm", se=FALSE)
qplot(votes_percent2015/popular_vote2015,votes_percent/popular_vote,data=Combined[!is.na(interaction(name,party_name))][party_name != "Green"], col=party_name, alpha=I(0.5), geom="density_2d") +
  geom_point() + scale_party_colours + facet_grid(party_name~name) + geom_rug() + geom_smooth(method="lm", se=FALSE) + scale_x_log10() + scale_y_log10()
qplot(-order2015,-order,data=Combined[!is.na(interaction(name,party_name))][party_name != "Green"], col=party_name, alpha=I(0.5), geom="density_2d") +
  geom_point() + scale_party_colours + facet_grid(party_name~name) + geom_rug() + geom_smooth(method="lm", se=FALSE)

qplot(-order2015,-order,
      data=Combined[!is.na(interaction(name,party_name))][party_name != "Green"][, c(.SD, N=.N), by=c("name","party_name","order","order2015")],
      col=party_name, label=N, alpha=I(0.5), geom="text") +
  scale_party_colours + facet_grid(party_name~name) + scale_x_continuous(breaks=-(1:20)) + scale_y_continuous(breaks=-(1:20))