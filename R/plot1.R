f <- function(x,a,b) 1 - (1 - x ** exp(a)) ** exp(b)
#f <- function(x,a,b) pbeta(x,exp(a),exp(b))
custom_curve_fit <- function(data) {
  custom_fit <- function(p, dd) sum((dd$y - f(dd$x, p[1], p[2]))^4, na.rm=TRUE)
  s <- data[,.(x=popular_vote_percent/100,y=votes_percent/100)][!is.na(x+y)]
  
  best <- c(0, 0)
  bestv <- 1e50
  for (a in seq(-4, 4, 0.1)) {
    for (b in seq(-4, 4, 0.1)) {
      v <- custom_fit(c(a, b), s)
      if (v < bestv) {
        bestv <- v
        best <- c(a, b)
      }
    }
  }
  print(best)
  print(bestv)
  optim(best, custom_fit, dd=s, method="SANN", control=list(maxit=1000, ndeps=c(1e-8,1e-8)))
}
data <- PECRE[election_id>"F1980" & votes_percent>5]
riding <- sample(data$riding_id, 1)
party <- sample(data[riding_id==riding]$party, 1)
data <- data[riding_id == riding & party_name == party]
fit <- custom_curve_fit(data)
xs <- 100*seq(0,1,0.002)
ys <- 100*f(xs/100, fit$par[1], fit$par[2])
qplot(xs, ys, geom="line", col=I("red")) + geom_point(aes(x=votes_percent, y=popular_vote_percent), data=data)
fit
c(riding, party)


# ---------------------------------------

slopes_swing <- PECRE[
  !is.na(popular_vote_percent)&!is.na(votes_percent)&party_name%in%parties&election_id>"F2005",
  .(election_id,party_name,riding_id,ratio=votes_percent/popular_vote_percent)]
slopes_comparison <- slopes[slopes_swing[,.(party_name,riding_id,ratio=mean(ratio, na.rm=TRUE) ),by=c("riding_id","party_name")], on=c("riding_id","party_name")] 
qplot(slope,ratio,data=slopes_comparison)

ggplot(aes(x=ratio, col=party_name), data=slopes_swing) + geom_density() +
  scale_party_colours + xlim(0,5) + facet_grid(party_name ~ .) +
  geom_vline(aes(xintercept=m), data=slopes_swing[,.(m=mean(ratio)),by="party_name"],
             col="red", linetype="dashed", size=0.5) +
  theme(legend.position="none")
