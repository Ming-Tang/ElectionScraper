perform_fit_uniform <- function(.SD, .N) {
  latest <- .SD[1]
  list(n=.N, slope=1, intercept=latest$votes_percent - latest$popular_vote_percent)
}

perform_fit_proportional <- function(.SD, .N) {
  latest <- .SD[1]
  list(n=.N, slope=latest$votes_percent / latest$popular_vote_percent, intercept=0)
}

seat_projection_model <- function(data, recent, perform_fit=NULL, mode="lm") {
  if (is.null(perform_fit))
    perform_fit <- function(.SD, .N) {
      latest <- .SD[1]
      tryCatch({
        if (mode != "lm")
          stop("swing")
        model <- lm(
          votes_percent ~ popular_vote_percent, data=.SD,
          na.action=na.exclude, singular.ok=TRUE)

        slope <- coef(model)["popular_vote_percent"]
        intercept <- coef(model)["(Intercept)"] 
        
        # Adjust intercept so that the line crosses most recent results
        if (FALSE) {
          x_at_latest <- latest$popular_vote_percent
          y_at_latest <- latest$votes_percent
          model_y_at_latest <- slope * x_at_latest + intercept
          intercept <- intercept - (model_y_at_latest - y_at_latest)
        }

        if (is.na(slope + intercept))
          stop("NA")

        list(n=.N, slope=slope, intercept=intercept)
      }, error=function(e) {
        if (mode == "uniform") {
          # fallback to uniform swing
          list(n=.N, slope=1, intercept=latest$votes_percent - latest$popular_vote_percent)
        } else {
          # fallback to proportional swing
          list(n=.N, slope=latest$votes_percent / latest$popular_vote_percent, intercept=0)
        }
      })
    }

  setorder(data, riding_id, party_name, -election_id)
  models <- data[,
    perform_fit(.SD, .N),
    by=c("party_name", "riding_id")
  ]

  models <- models[recent, on=c("party_name","riding_id")]

  models[
    is.na(slope + intercept),
    #`:=`(slope = mean(votes_percent, na.rm=TRUE)/mean(popular_vote_percent, na.rm=TRUE), intercept = 0),
    `:=`(intercept = mean(votes_percent, na.rm=TRUE) - mean(popular_vote_percent, na.rm=TRUE), slope = 1),
    by=c("riding_id", "party_name")
  ]
  models[slope<0, slope:=0.5]
  models[,polling_popular_vote_percent := NA_real_][,predicted_votes_percent := NA_real_]
  models
}

project_seats <- function(models, polling, model_func=NA) {
  if (is.na(model_func)) {
    model_func <- function(pv, slope, intercept) {
      y <- (pv * slope + intercept)
      # perform interpolations so that f(0) = 0, f(100) = 100
      # lower Q, R means smoother curves
      if (TRUE) {
        k <- 120
        Q <- k + pmin(pmax(0, 2 * intercept), k)
        R <- k
        y <- 100 + (y * tanh(Q * pv / 100) - 100) * tanh(R * (1 - pv /100))
      }
      pmin(pmax(0, y), 100)
    }
  }

  models$polling_popular_vote_percent <- polling[models$party_name, on="party_name"]$popular_vote_percent
  models[, predicted_votes_percent := model_func(polling_popular_vote_percent, slope, intercept)]

  setorder(models, riding_id, -predicted_votes_percent)
  models[, predicted_order := (1:.N) - 1, by="riding_id"]

  winners <- models[predicted_order==0]
  setorder(winners, riding_id, party_name)
  seats <- winners[
    ,.(seat_projection=.N),
    by="party_name"
  ][polling, on="party_name"][is.na(seat_projection), seat_projection := 0]
  
  get_changes <- function() {
    models[
      ,.(prev_winner=.SD[order==0]$party_name, new_winner=.SD[predicted_order==0]$party_name),
      by="riding_id"]
  }
  list(models=models, winners=winners, seats=seats, get_changes=get_changes)
}

normalize_percents <- function(xs) xs * 100 / sum(xs)
clamp_percents <- function(xs) pmin(pmax(0, xs), 100)
#deviate <- function(percents, sd=1) normalize_percents(pmin(pmax(0, percents + rnorm(5, mean=0, sd=sd)),100))
deviate <- function(percents, sd=1, n=1) {
  N <- as.integer(1000 / sd*sd) + 1L
  t(100 * rmultinom(n, N, percents/100) / N)
}
  
gallagher <- function(data) {
  total_seats <- sum(data$seat_projection)
  data[, seat_percent := 100 * seat_projection / total_seats][
    , diff2 := (popular_vote_percent - seat_percent) ** 2][
    , ratio := diff2 / popular_vote_percent]
  ss <- sum(data$diff2)
  sli <- sum(data$ratio)
  list(gi=sqrt(ss / 2), sli=sli)
}

#profvis(for(i in 1:1000){project_seats(models, polling)})