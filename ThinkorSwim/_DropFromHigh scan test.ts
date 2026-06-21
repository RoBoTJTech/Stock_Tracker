# Drop from high tracker required for everything
# Version 25.1202
# Track to find high, then follows to
# find dip below threshold.
input thresholdValue = 1;
input bidPriceOffsetValue = 0.01;
input tradingType = {default Intraday, EndOfDay};

input useGuard = yes;
def intraday = tradingType == tradingType.Intraday;

def sellPriceTracker;
##### UNCOMMENT IF USED ON ORDER ONLY VERSION #####
#sellPriceTracker = Double.NaN;
#def studyMode = no;
###################################################


###### UNCOMMENT IF USED FOR STRATEGY VERION ######
input studyType = {default Strategy, Order};
def strategy = studyType == studyType.Strategy;
###################################################
input strategyPeriodOverrideDays = 0;  # 0 = default behavior
def SMALow = Average(low[1], 10);
def EMALow = ExpAverage(low[1], 10);
def SMAHigh = Average(high[1], 20);
def EMAHigh = ExpAverage(high[1], 20);

def history = Average(close[1], 300);

def isNewDay = GetYYYYMMDD() != GetYYYYMMDD()[1];

def dailyOpen = if IsNaN(dailyOpen[1]) or dailyOpen[1] == 0 then open [1]
    else if isNewDay then close[1]
    else dailyOpen[1];

#def percentChange = if IsNaN(dailyOpen) or IsNaN(low[1]) #or dailyOpen == 0 then 0 else 100 * (low[1] - dailyOpen) / dailyOpen;

def percentChange =
if intraday then
    if IsNaN(dailyOpen) or IsNaN(low[1]) or dailyOpen == 0 then 0
    else 100 * (low[1] - dailyOpen) / dailyOpen
else
    if IsNaN(close[1]) or close[1] == 0 then 0
    else 100 * (open - close[1]) / close[1];

def allConditionsMet;
def isInMarketHours;
def latestTime = HighestAll(GetTime());
def latestDate = HighestAll(GetYYYYMMDD());
def secondsFrom0930 = (latestTime - RegularTradingStart(latestDate)) / 1000;

def cutoffOverride = latestTime - (strategyPeriodOverrideDays * 86400000);

def cutoffTimeEndOfDay =
    if strategyPeriodOverrideDays > 0 and 
       strategyPeriodOverrideDays <= 365
    then cutoffOverride
    else latestTime - (365 * 86400000);

# isInMarketHours (re-structured: strategy first)

if strategy
then {
    if intraday
    then {
        isInMarketHours =
        (
            (percentChange >= 0 and SecondsFromTime(0930) >= 0 and SecondsTillTime(1600) > 0) or
            (percentChange <  0 and SecondsFromTime(0945) >= 0 and SecondsTillTime(1600) > 0)
        )
        and
        (
            ((strategyPeriodOverrideDays <= 0 
                or strategyPeriodOverrideDays > 365)
                and GetTime() >=
                (latestTime
                 - (
                    (Max(5 - GetDayOfWeek(latestDate), 1)
                     + (if secondsFrom0930 < 11700 then 1 else 0)) * 86400000
                   )
                 - (if GetDayOfWeek(latestDate)
                    - (if secondsFrom0930 < 11700 then 1 else 0) < 3
                  then 172800000 else 0)
                )
            )
            or
            (strategyPeriodOverrideDays > 0
                and strategyPeriodOverrideDays <= 365 
                and GetTime() >= cutoffOverride)
        );
    } else {
        isInMarketHours = GetTime() >= cutoffTimeEndOfDay;
    }
} else {
    if intraday
    then {
        isInMarketHours =
            (percentChange >= 0 and SecondsFromTime(0930) >= 0 and SecondsTillTime(1600) > 0) or
            (percentChange <  0 and SecondsFromTime(0945) >= 0 and SecondsTillTime(1600) > 0);
    } else {
        isInMarketHours = yes;
    }
}

def highestPrice = if (percentChange < -100 and SecondsFromTime(930) >= 0 and SecondsTillTime(945) > 0) or IsNaN(highestPrice[1]) or allConditionsMet[1]
    then 0 else Max(high[1], highestPrice[1]);
def highCounter = if IsNaN(highCounter[1]) or highestPrice != highestPrice[1] then 0 else highCounter[1] + 1;

def threshold = highestPrice * thresholdValue / 100;

#Conditions for Sell
# chart States 0 = flat, 1 = rising, -1 = falling
def chartState = if isInMarketHours and 
    percentChange > 1 then 1
    else if isInMarketHours and
    percentChange < 0 then -1
    else 0;#if isInMarketHours then 0
    #else Double.NaN;

if  chartState > 0 and
    close[1] > open[1] and high[1] - close[1] < close[1] - low[1] and (close[2] >= open[2] or EMALow > SMALow) and 
    (highCounter >= 1 or IsNaN(sellPriceTracker[1])) and highCounter < 6 and 
   EMAHigh > SMAHigh
then {
    allConditionsMet = yes;
}
else if chartState < 0 and
    highestPrice - close[1] > threshold and
    close[1] > close[2] and 
    close[1] >= SMALow and close[2] < SMALow
then {
    allConditionsMet = yes;
}
else if isInMarketHours and chartState == 0 and 
    highestPrice - close[1] > threshold and 
    close[1] > open[1] and open[1] < open[2]
then {
    allConditionsMet = yes;
}
else {
    allConditionsMet = no;
}

def trendOpen =
    if chartState > 0 and allConditionsMet[1] then
            Min(open[1], open)
    else
        open;

def guardHit =
    close > trendOpen
        + (trendOpen * (thresholdValue / 100) * 0.5)  # 1/2 of threshold
        + 0.01;

def guardOK = !useGuard or !guardHit;

plot buySellTrigger =
    if intraday then
        if (allConditionsMet or allConditionsMet[1]) and guardOK then 1 else 0
    else
        if allConditionsMet and !allConditionsMet[1] and guardOK then 1 else 0;

##################################################
### Remove all below from _DropFromHigh_Order  ###
##################################################

input bidPrice = {default Bid, Mark, Ask};
input showDetails = yes;
input showPlots = {Buy, default Sell, Trackers, Averages, Volume, All};

def plotLevel;
if showPlots == showPlots.Volume
then {
    plotLevel = -1;
}
else if showPlots == showPlots.Buy
then {
    plotLevel = 0;
}
else if showPlots == showPlots.Sell
then {
    plotLevel = 1;
}
else if showPlots == showPlots.Trackers
then {
    plotLevel = 2;
}
else if showPlots == showPlots.Averages
then {
    plotLevel = 3;
}
else {
    plotLevel = 4;
}

AssignPriceColor(
        if chartState > 0 then
            Color.CYAN
        else if chartState < 0 then
            Color.YELLOW
        else if isInMarketHours then 
            Color.CURRENT 
        else 
        if close <= open then 
            Color.PINK 
        else if close > open then 
            Color.LIGHT_GREEN 
        else 
            Color.DARK_GRAY);

# Sell PriceActionIndicator Tracking
def sold;
if high >= sellPriceTracker[1]
then {
    sold = yes;
} else {
    sold = no;
}

def buyPrice = (
    if bidPrice == bidPrice.Bid then
        (if !IsNaN(open(priceType = PriceType.BID)) then open(priceType = PriceType.BID) else open)
    else if bidPrice == bidPrice.Mark then
        (if !IsNaN(open(priceType = PriceType.MARK)) then open(priceType = PriceType.MARK) else open)
    else
        (if !IsNaN(open(priceType = PriceType.ASK)) then open(priceType = PriceType.ASK) else open)
) + bidPriceOffsetValue;


# Remember a missed buy when signal fires but low > buyPrice.
# Keep it until price tags that level; also clear if a position exists.
def failedBuyTracker = CompoundValue(
    1,
    if !isInMarketHours then
        Double.NaN
    else if IsNaN(failedBuyTracker[1]) then
        if allConditionsMet and IsNaN(sellPriceTracker[1]) and low > buyPrice
        then buyPrice
        else Double.NaN
    else
        if low <= failedBuyTracker[1] or !IsNaN(sellPriceTracker[1])
        then Double.NaN
        else failedBuyTracker[1],
    Double.NaN
);

# Block entries while a failed level is pending
def enteredTrade =
    allConditionsMet
     and IsNaN(sellPriceTracker[1])
     and IsNaN(failedBuyTracker)
     and buyPrice >= low;

def prevFailed = if IsNaN(failedBuyTracker[1]) then 0 else failedBuyTracker[1];
def enteredFromFailed =
    !IsNaN(failedBuyTracker[1]) and
    low <= prevFailed and
    IsNaN(sellPriceTracker[1]) and
    isInMarketHours;

def entryPrice = if enteredFromFailed then failedBuyTracker[1] else buyPrice;

def activeBuyPrice =
    if enteredTrade or enteredFromFailed then entryPrice
    else if sold[1] then Double.NaN
    else activeBuyPrice[1];

    # Chart-only dividend data: blank for Intraday mode.
def nextDividend = if intraday then Double.NaN else GetDividend()[-1];
    
# nextDividend is always NaN in Intraday mode, so no dividend adjustment is made.
sellPriceTracker = if enteredTrade or enteredFromFailed then entryPrice + ( entryPrice * thresholdValue / 100) else if !IsNaN(nextDividend) and !IsNaN(sellPriceTracker[1]) then Ceil(activeBuyPrice[1]) else if sold[1] then Double.NaN else sellPriceTracker[1];

#def sellCount = if (sellingHigh and !sellingHigh[1]) then sellCount[1] + 1 else sellCount[1];
def sellCount = CompoundValue(1,
    if sold and !sold[1] then sellCount[1] + 1 else sellCount[1],
    0
);


def buyCount = if enteredTrade or enteredFromFailed then buyCount[1] + 1 else buyCount[1];

AddChartBubble(showDetails and !sold[1] and sold and sellCount > 0, sellPriceTracker[1],  "#" + sellCount + ": " + Round(sellPriceTracker[1], 2), Color.LIGHT_GREEN, yes);

def triggerCount = if allConditionsMet then triggerCount[1] + 1 else triggerCount[1];

def sellPriceAvgcount = CompoundValue(1, sellPriceAvgcount[1] + 1, 0);

# Time Tracking and Metrics
def lastBuyDay = CompoundValue(
    1,
    if !IsNaN(sellPriceTracker) and isInMarketHours then GetYYYYMMDD() else lastBuyDay[1],
    0
);

def buyDaysCount = CompoundValue(
    1,
    buyDaysCount[1] + (if !IsNaN(sellPriceTracker) and isInMarketHours and lastBuyDay[1] != GetYYYYMMDD() then 1 else 0),
    0
);

def buyProfit = CompoundValue(

    1,

    if sold and !sold[1] then

        buyProfit[1] + ((sellPriceTracker[1] - activeBuyPrice[1]) / activeBuyPrice[1] * 100)

    else

        buyProfit[1],

    0

);

def profit252 =
    if buyDaysCount > 0
    then Round((252 / buyDaysCount) * buyProfit, 2)
    else 0;

def clearScore = if sellCount >= 4 then 1 else 0;

def productivityScore = Round(
    (
        (buyCount / Ceil((triggerCount + 1 - buyCount) / 2)) *
        (buyProfit / 100) *
        (profit252 / 100) *
        (Log(triggerCount - buyCount + 1) + 1) / 10
    ) * 100 * clearScore, 2
);

# Plots and lines
plot scanScorePlot =
    if plotLevel >= 4 then
        if !intraday and chartState > 0 #and (GetDayOfWeek(latestDate) == 5 or GetDayOfWeek(latestDate) == 1)
        then sellCount * 1.5
        else sellCount
    else Double.NaN;


plot SMALowPlot =  if plotLevel >= 3 then SMALow else Double.NaN;
SMALowPlot.AssignValueColor(Color.ORANGE);
plot EMALowPlot = if plotLevel >= 3 then EMALow else Double.NaN;

EMALowPlot.AssignValueColor(Color.YELLOW);

plot SMAHighPlot = if plotLevel >= 3 then SMAHigh else Double.NaN;

SMAHighPlot.AssignValueColor(Color.BLUE);

plot EMAHighPlot = if plotLevel >= 3 then EMAHigh else Double.NaN;

EMAHighPlot.AssignValueColor(Color.CYAN);

plot highestPriceLine = if plotLevel >= 2 and highestPrice > 0 and highestPrice[1] == highestPrice then highestPrice else Double.NaN;
highestPriceLine.SetDefaultColor(Color.WHITE);
highestPriceLine.SetStyle(Curve.FIRM);
highestPriceLine.SetLineWeight(1);

plot sellPriceLine = if plotLevel >= 1 then sellPriceTracker else Double.NaN;
sellPriceLine.SetDefaultColor(Color.RED);
sellPriceLine.SetStyle(Curve.FIRM);
sellPriceLine.SetLineWeight(2);

plot failedBuyLine = if plotLevel >= 1 then failedBuyTracker else Double.NaN;
failedBuyLine.SetDefaultColor(Color.LIGHT_GRAY);
failedBuyLine.SetStyle(Curve.FIRM);
failedBuyLine.SetLineWeight(2);

plot buyArrowPlot = if allConditionsMet and plotLevel > 0 then low - .10 else Double.NaN;
buyArrowPlot.SetPaintingStrategy(PaintingStrategy.ARROW_UP);
buyArrowPlot.SetLineWeight(5);
buyArrowPlot.AssignValueColor(
    if enteredTrade then
        (if chartState > 0 then Color.CYAN
         else if chartState < 0 then Color.YELLOW
         else Color.GREEN)
    else if !IsNaN(sellPriceTracker[1]) or !IsNaN(failedBuyTracker[1]) then
        Color.DARK_GRAY     # trigger ignored: already in position
    else
        Color.LIGHT_GRAY    # trigger but no entry
);

# Labels for Metrics

def pale = 180;

def t0_10    = Min(Max(productivityScore / 10, 0), 1);
def t10_50   = Min(Max((productivityScore - 10) / 40, 0), 1);
def t50_100  = Min(Max((productivityScore - 50) / 50, 0), 1);
def t100_500 = Min(Max((productivityScore - 100) / 400, 0), 1);

def r =
    if IsNaN(productivityScore) or productivityScore <= 0 then 90
    else if productivityScore < 10 then 255                          # white->yellow keeps r=255
    else if productivityScore < 50 then 0                            # green band
    else if productivityScore < 100 then 255                         # magenta band
    else if productivityScore < 500 then 0                           # blue band
    else 0;

def g =
    if IsNaN(productivityScore) or productivityScore <= 0 then 90
    else if productivityScore < 10 then 255                          # white->yellow keeps g=255
    else if productivityScore < 50 then 255                          # green band stays g=255
    else if productivityScore < 100 then
        Round(pale * (1 - t50_100), 0)                               # pale->0 (pale magenta -> magenta)
    else if productivityScore < 500 then
        Round(pale * (1 - t100_500), 0)                              # pale->0 (pale blue -> blue)
    else 0;

def b =
    if IsNaN(productivityScore) or productivityScore <= 0 then 90
    else if productivityScore < 10 then
        Round(255 * (1 - t0_10), 0)                                  # 255->0 (white->yellow)
    else if productivityScore < 50 then
        Round(pale * (1 - t10_50), 0)                                # pale->0 (pale green -> green)
    else if productivityScore < 500 then
        255                                                          # magenta + blue both keep b=255
    else 255;

AddLabel(
    showDetails, 
    thresholdValue + "% Score: " + 
    productivityScore + ", " +
    "Active Days: " + buyDaysCount + ", " + 
    "Active Return: " + profit252 + "%" +
    if profit252 < 10 then "           " 
    else if profit252 < 100 then "          " 
    else if profit252 < 1000 then "         " 
    else if profit252 < 10000 then "        "
    else if profit252 < 100000 then "       " 
    else " ", 
    CreateColor(
        r,
        g,
        b
    )
);

AddLabel(showDetails, "Triggers: " + triggerCount +  
    if triggerCount < 10 then "    "
    else if triggerCount < 100 then "     "
    else if triggerCount < 1000 then "    "
    else if triggerCount < 10000 then "   "
    else if triggerCount < 100000 then "  "
    else " " , Color.CYAN);

AddLabel(yes, "Buys: " + buyCount + 
    if buyCount < 10 then "      "
    else if buyCount < 100 then "     "
    else if buyCount < 1000 then "    "
    else if buyCount < 10000 then "   "
    else if buyCount < 100000 then "  "
    else " ", Color.LIGHT_GREEN);

AddLabel(showDetails, "Sells: " + sellCount + " Gain: " +
    (if buyProfit == Round(buyProfit, 0)
    then buyProfit
    else Round(buyProfit, 1)) + "%" +
    if buyProfit < 10 then "        "
    else if buyProfit < 100 then "       "
    else if buyProfit < 1000 then "      "
    else if buyProfit < 10000 then "     "
    else if buyProfit < 100000 then "    "
    else " ",
    if buyProfit >= 52 then 
        Color.YELLOW else Color.LIGHT_RED);

Alert(showDetails and allConditionsMet and thresholdValue == 1, "threshold trigger point: $" + open, Alert.BAR, Sound.Bell);


# --- Compact Date for Swing Score (yymmdd) ---
def chartStart =
    if BarNumber() == 1 then GetYYYYMMDD() else chartStart[1];

def year  = Floor(chartStart / 10000);          # 2025
def yy    = year - 2000;                        # 25
def mm    = Floor(chartStart % 10000 / 100);    # 11
def dd    = chartStart % 100;                   # 06, 20, etc.

plot mh =
    if isInMarketHours
    then (HighestAll(high) + LowestAll(low)) / 2
    else Double.NaN;

mh.SetPaintingStrategy(PaintingStrategy.LINE);
mh.SetLineWeight(1);
mh.SetStyle(Curve.MEDIUM_DASH);
mh.AssignValueColor(Color.DARK_GREEN);

def chartStartFloat = yy * 10000 + mm * 100 + dd;

plot swingScoreDatePlot =
    if plotLevel >= 4 then chartStartFloat else Double.NaN;

plot dividendDot =
    if !IsNaN(nextDividend) then close else Double.NaN;

dividendDot.SetPaintingStrategy(PaintingStrategy.POINTS);

dividendDot.SetLineWeight(5);

dividendDot.SetDefaultColor(Color.MAGENTA);