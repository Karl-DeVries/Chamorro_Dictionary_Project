library(ggplot2)


# Load up the data
TestData <- read.csv(file = "~/Chamorro_Dictionary_Project/Tests/SystemTests.csv", header = TRUE, sep = ",")

# Take a look at it:
#str(TestData)
#summary(TestData)

#We have Queries along with their expected entries, we also have the rank assigned to the entry
#by different systems. The EditDistance system ranks entries by their edit distance
#the RatioOnly system ranks entries by R/O distance
#the Ratio_Parse system uses takes the R/O distance after affixes have been stripped

# We have one observation for each of four systems
obs.per.system <- length(TestData$Rank) / 4

# Decide How many cutoffs we want
n.bins <- 10
bins <- 1:n.bins
systems <- c("EditDistance", "Ratio", "Ratio_spread", "Ratio_strip")

# Now we see how our recall does for the correct result showing up in the top one...ten spots
BinRes <- data.frame(list("System" = rep(systems, 10), "TopN" = rep(bins, each = 4)))

n.rows <- n.bins * 4
BinRes$Recall <- NA

for (i in 1:n.rows) {
  sys <- BinRes$System[i]
  cut <- BinRes$TopN[i]
  sub <- subset(TestData, System == sys & Rank <= cut)
  BinRes$Recall[i] <- length(sub$Rank) 
}

BinRes$Proportion <- BinRes$Recall / obs.per.system

# Plot the results
plot <- ggplot(data = BinRes, aes(x = TopN, y = Proportion, color = System))
plot <- plot + geom_line() + geom_point()
plot <- plot + scale_x_continuous(breaks = seq(1, 10, by = 1))
plot <- plot + scale_y_continuous(breaks = seq(.5, 1, by = .1), limits = c(.6, 1))
plot <- plot + ggtitle("% Correct Recall") + labs(x = "Within top n results", y = "Proportion Recalled")
plot <- plot + theme_bw() +
          theme(axis.text = element_text(size = 12),
                legend.key = element_rect(fill = "white"),
                legend.background = element_rect(fill = "white"),
                panel.grid.minor = element_blank()
               )
plot

#The plot shows how many of the expected results are being returned within the top one to ten results
#We see that the ratio system is doing better than the EditDistance metric and that the affix stripper 
#improves on the ratio system