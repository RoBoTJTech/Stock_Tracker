# Auto Trader  
# Version 1.1.0 ~ July 26, 2024
# Track to find high, then follows to
# find dip below threshold.
#declare once_per_bar;
input thresholdValue = 1;
input sellPriceOffsetValue = 0;
input triggerOffset = no;
input enableSafetyNet = yes;
input resetHighOnOpenValue = no;

# Market Hours
input marketOpenValue = 0930;
input marketCloseValue = 1600;
input excludeFridayValue = no;

input showDetails = yes;

# Time and Price Definitions
def isFourHoursOrGreaterChart = GetAggregationPeriod() >= AggregationPeriod.FOUR_HOURS;
def isInMarketHours = if isFourHoursOrGreaterChart and !(excludeFridayValue and GetDayOfWeek(GetYYYYMMDD()) == 5) then yes
                      else SecondsFromTime(marketOpenValue) >= 0 and SecondsTillTime(marketCloseValue) > 0 and !(excludeFridayValue and GetDayOfWeek(GetYYYYMMDD()) == 5);

# Heikin Ashi Calculations
def allConditionsMet;

def highestPrice = if IsNaN(highestPrice[1]) or allConditionsMet[1] or allConditionsMet[2] 
    or (! isInMarketHours and resetHighOnOpenValue) then 0 else Max(high[1], highestPrice[1]);
#alert(highestPrice != highestPrice[1], "Highest Price Changed to " + highestPrice, alert.BAR, Sound.Bell);



# Calculate percentage change from daily open to current close for QQQ, SPY, and DIA
def isNewDay = GetYYYYMMDD() != GetYYYYMMDD()[1];

def dailyOpen = if IsNaN(dailyOpen[1]) then open(period = AggregationPeriod.DAY)
                else if isNewDay then open
                else dailyOpen[1];
def dwcfDailyOpen = if isNewDay or IsNaN(dwcfDailyOpen[1]) then open(symbol = "$DWCF", period = AggregationPeriod.DAY) else dwcfDailyOpen[1];
def spyDailyOpen = if isNewDay or IsNaN(spyDailyOpen[1]) then open(symbol = "SPY", period = AggregationPeriod.DAY) else spyDailyOpen[1];
def compDailyOpen = if isNewDay or IsNaN(compDailyOpen[1]) then open(symbol = "$COMP", period = AggregationPeriod.DAY) else compDailyOpen[1];
def djiDailyOpen = if isNewDay or IsNaN(djiDailyOpen[1]) then open(symbol = "$DJI", period = AggregationPeriod.DAY) else djiDailyOpen[1];

def percentChange = if IsNaN(dailyOpen) or IsNaN(low) then 0 else 100 * (low - dailyOpen) / dailyOpen;
def dwcfPercentChange = if IsNaN(dwcfDailyOpen) or IsNaN(low(symbol = "$DWCF")) then 0 else 100 * (low(symbol = "$DWCF") - dwcfDailyOpen) / dwcfDailyOpen;
def spyPercentChange = if IsNaN(spyDailyOpen) or IsNaN(low(symbol = "SPY")) then 0 else 100 * (low(symbol = "SPY") - spyDailyOpen) / spyDailyOpen;
def compPercentChange = if IsNaN(compDailyOpen) or IsNaN(low(symbol = "$COMP")) then 0 else 100 * (low(symbol = "$COMP") - compDailyOpen) / compDailyOpen;
def djiPercentChange = if IsNaN(djiDailyOpen) or IsNaN(low(symbol = "$DJI")) then 0 else 100 * (low(symbol = "$DJI") - djiDailyOpen) / djiDailyOpen;

def marketPercentChange = Min(Min(Min(dwcfPercentChange, spyPercentChange), Min(compPercentChange, djiPercentChange)), 0);

def marketIndex;
if marketPercentChange == dwcfPercentChange {
    marketIndex = 1;
} else if marketPercentChange == spyPercentChange {
    marketIndex = 2;
} else if marketPercentChange == compPercentChange {
    marketIndex = 3;
} else if marketPercentChange == djiPercentChange {
    marketIndex = 4;
}
else {
    marketIndex = 0;
}

def threshold = highestPrice * thresholdValue / 100;
def safetyNet = if enableSafetyNet then (if marketPercentChange < 0 and percentChange < 0 then highestPrice * marketPercentChange / 100 else 0) else 0;
#Conditions for Sell
allConditionsMet = highestPrice - high[1] + safetyNet > threshold 
    and isInMarketHours and 
    (
        (high>high[1] and open[1] < open[2] and (!enableSafetyNet or percentChange >= 0)) or 
        (enableSafetyNet and percentChange < 0 and high>high[1] and open[1] > close[2] and open[2] > close[3])
    );

AssignPriceColor(if isInMarketHours and enableSafetyNet and safetyNet >= 0 and percentChange < 0 then Color.YELLOW
        else 
        if isInMarketHours and enableSafetyNet and safetyNet < 0 
            and percentChange < 0  then Color.ORANGE
        else
        if isInMarketHours then 
            Color.CURRENT 
        else 
        if close < open then 
            Color.PINK 
        else if close > open then 
            Color.LIGHT_GREEN 
        else 
            Color.DARK_GRAY);

# Sell Tracking
def sellPriceTracker;

# Sell PriceActionIndicator Tracking
def sellingHigh;
if high >= sellPriceTracker[1] then {
    sellingHigh = yes;
} else {
    sellingHigh = no;
}

sellPriceTracker = if allConditionsMet and IsNaN(sellPriceTracker[1]) then high[1] + ( high[1] * ( thresholdValue + sellPriceOffsetValue ) / 100) else if sellingHigh[1] then Double.NaN else sellPriceTracker[1];

def sellCount = if (sellingHigh and !sellingHigh[1]) then sellCount[1] + 1 else sellCount[1];

def buyCount = if allConditionsMet and IsNaN(sellPriceTracker[1]) then buyCount[1] + 1 else buyCount[1];

AddChartBubble(showDetails and !sellingHigh[1] and sellingHigh and sellCount > 0, sellPriceTracker[1],  "#" + sellCount + ": " + Round(sellPriceTracker[1], 2), Color.LIGHT_GREEN, yes);

# Buy Orders and Averages
def triggerCount = CompoundValue(1, if allConditionsMet then triggerCount[1] + 1 else triggerCount[1], 0);

# Sell Price Averages
def sellPriceAvgcount = CompoundValue(1, sellPriceAvgcount[1] + 1, 0);

# Plots and lines

plot buySellTrigger = if (! triggerOffset or (triggerOffset and !IsNaN(sellPriceTracker[1] and !IsNaN(sellPriceTracker)))) 
    and allConditionsMet then high[1] else 0;

plot highPricePlot = if allConditionsMet then highestPrice else Double.NaN;
highPricePlot.SetPaintingStrategy(PaintingStrategy.POINTS);
highPricePlot.SetLineWeight(3);
highPricePlot.SetDefaultColor(Color.WHITE);

plot highestPriceLine = if highestPrice > 0 and highestPrice[1] == highestPrice then highestPrice else Double.NaN;
highestPriceLine.SetDefaultColor(Color.WHITE);
highestPriceLine.SetStyle(Curve.LONG_DASH);
highestPriceLine.SetLineWeight(2);

plot thresholdPriceLine = if !IsNaN(highestPriceLine) then highestPrice - threshold else Double.NaN;
thresholdPriceLine.SetDefaultColor(Color.CYAN);
thresholdPriceLine.SetStyle(Curve.LONG_DASH);
thresholdPriceLine.SetLineWeight(2);

plot sellPricePlot = if allConditionsMet then high[1] + ( high[1] * ( thresholdValue + sellPriceOffsetValue ) / 100) else Double.NaN;
sellPricePlot.SetPaintingStrategy(PaintingStrategy.POINTS);
sellPricePlot.SetLineWeight(3);
sellPricePlot.SetDefaultColor(Color.RED);

plot sellPriceLine = sellPriceTracker;
sellPriceLine.SetDefaultColor(Color.RED);
sellPriceLine.SetStyle(Curve.FIRM);
sellPriceLine.SetLineWeight(2);

plot buyPricePlot = if allConditionsMet then high[1] else Double.Nan;
buyPricePlot.SetPaintingStrategy(PaintingStrategy.POINTS);
buyPricePlot.SetLineWeight(3);
buyPricePlot.SetDefaultColor(Color.GREEN);

plot buyArrowPlot = if allConditionsMet then high[1] else Double.NaN;
buyArrowPlot.SetPaintingStrategy(PaintingStrategy.ARROW_UP);
buyArrowPlot.SetLineWeight(5);
buyArrowPlot.SetDefaultColor(Color.GREEN);

# Time Tracking and Metrics
def totalDays = CompoundValue(1, totalDays[1] + isNewDay, 1);

def lastBuyDay;
if sellPriceTracker then {
    lastBuyDay = GetYYYYMMDD();
} else {
    lastBuyDay = lastBuyDay[1];
}
def buyDaysCount;
if lastBuyDay[1] != GetYYYYMMDD() and sellPriceTracker then {
    buyDaysCount = buyDaysCount[1] + 1;
} else { 
    buyDaysCount = buyDaysCount[1];
}
# Labels for Metrics
def buyProfit = ( thresholdValue + sellPriceOffsetValue ) * sellCount;
def triggerProfit = (thresholdValue + sellPriceOffsetValue) * (buyCount + Floor((triggerCount - buyCount) / 2));

AddLabel(yes, "Buys: " + buyCount + 
    if buyCount < 10 then "        "
    else if buyCount < 100 then "       "
    else if buyCount < 1000 then "      "
    else if buyCount < 10000 then "     "
    else if buyCount < 100000 then "    "
    else " ", Color.LIGHT_GREEN);

def annualFactor = if totalDays > 252 then totalDays / 252 else 1;
def profit252 = Round((252 / buyDaysCount) * buyProfit / annualFactor, 2);

def productivityScore = Round(
    (
        (buyCount / Ceil((triggerCount + 1 - buyCount) / 2)) *
        (buyProfit / 100) *
        (profit252 / 100) *
        (Log(triggerCount - buyCount + 1) + 1) / 10
    ) * 100, 2
);

AddLabel(showDetails, "Sells: " + sellCount + ", Gained: " + 
    buyProfit + "%" +
    if buyProfit < 10 then "          "
    else if buyProfit < 100 then "         "
    else if buyProfit < 1000 then "        "
    else if buyProfit < 10000 then "       "
    else if buyProfit < 100000 then "      "
    else " ", Color.LIGHT_RED);

AddLabel(showDetails, "Working Days: " + buyDaysCount + ", " + 
    "Annual Trade Gain: " + profit252 +  "%, " +
    "Score: " + productivityScore +
    if profit252 < 10 then "             " 
    else if profit252 < 100 then "            " 
    else if profit252 < 1000 then "           " 
    else if profit252 < 10000 then "          "
    else if profit252 < 100000 then "         " 
    else " ", Color.WHITE);

AddLabel(showDetails, "Triggers: " + triggerCount + 
    if triggerCount - buyCount >= 8 then ", Est. w/ Offset Gains: " + 
    triggerProfit + "%         "
    else if triggerCount < 10 then "      "
    else if triggerCount < 100 then "       "
    else if triggerCount < 1000 then "      "
    else if triggerCount < 10000 then "     "
    else if triggerCount < 100000 then "    "
    else " " , Color.CYAN);

AddLabel(showDetails and percentChange > 0, GetSymbol() + ": " + Round(percentChange, 2) + "%      ", Color.LIGHT_GREEN);
AddLabel(showDetails and percentChange < 0, GetSymbol() + ": " + Round(percentChange, 2) + "%      ", Color.LIGHT_RED);

AddLabel(showDetails and marketPercentChange > 0 and marketIndex == 1, "$DWJC: " + Round(dwcfPercentChange, 2) + "%      ", Color.LIGHT_GREEN);
AddLabel(showDetails and marketPercentChange < 0 and marketIndex == 1, "$DWCJ: " + Round(dwcfPercentChange, 2) + "%      ", Color.LIGHT_RED);

AddLabel(showDetails and marketPercentChange > 0 and marketIndex == 2, "SPY: " + Round(spyPercentChange, 2) + "%      ", Color.LIGHT_GREEN);
AddLabel(showDetails and marketPercentChange < 0 and marketIndex == 2, "SPY: " + Round(spyPercentChange, 2) + "%      ", Color.LIGHT_RED);

AddLabel(showDetails and marketPercentChange > 0 and marketIndex == 3, "$COMP: " + Round(compPercentChange, 2) + "%      ", Color.LIGHT_GREEN);
AddLabel(showDetails and marketPercentChange < 0 and marketIndex == 3, "$COMP: " + Round(compPercentChange, 2) + "%      ", Color.LIGHT_RED);

AddLabel(showDetails and marketPercentChange > 0 and marketIndex == 4, "$DJI: " + Round(djiPercentChange, 2) + "%      ", Color.LIGHT_GREEN);
AddLabel(showDetails and marketPercentChange < 0 and marketIndex == 4, "$DJI: " + Round(djiPercentChange, 2) + "%      ", Color.LIGHT_RED);

AddLabel(showDetails and !enableSafetyNet, "No Safety Net    ", Color.YELLOW);
AddLabel(showDetails and safetyNet < 0 and percentChange < 0, "Threshold Safety Net: $" + Round(safetyNet, 2) + "      ", Color.LIGHT_RED);
AddLabel(showDetails and enableSafetyNet and percentChange < 0 and safetyNet >= 0, "3 Bar Safety Net      ", Color.YELLOW);
