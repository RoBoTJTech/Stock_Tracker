#Thresholds for triggers
#declare once_per_bar;
input resetHighOnOpenValue = yes;
input thresholdValue = 1;
input sellPriceOffsetValue = 0;
input triggerOffset = no;

# Market Hours
input marketOpenValue = 0930;
input marketCloseValue = 1600;
input excludeFridayValue = no;

# Definitions based on Input Type
def threshold;
def sellThreshold;

# Time and Price Definitions
def isFourHoursOrGreaterChart = GetAggregationPeriod() >= AggregationPeriod.FOUR_HOURS;
def isInMarketHours = if isFourHoursOrGreaterChart and !(excludeFridayValue and GetDayOfWeek(GetYYYYMMDD()) == 5) then yes
                      else SecondsFromTime(marketOpenValue) >= 0 and SecondsTillTime(marketCloseValue) > 0 and !(excludeFridayValue and GetDayOfWeek(GetYYYYMMDD()) == 5);

# Heikin Ashi Calculations
def HA_Close = (open[1] + high[1] + low[1] + close[1]) / 4;
def HA_Open = CompoundValue(1, (HA_Open[2] + HA_Close[2]) / 2, close);
def HA_High = Max(Max(high, HA_Open), HA_Close);
def HA_Low = Min(Min(low, HA_Open), HA_Close);
def conditionForTopWickOnly = HA_Close >= HA_Open and HA_High > HA_Close and HA_Low == Min(HA_Open, HA_Close);

AssignPriceColor(if isInMarketHours then 
            Color.CURRENT 
        else 
        if HA_Close < HA_Open then 
            Color.PINK 
        else if HA_Close > HA_Open then 
            Color.LIGHT_GREEN 
        else 
            Color.DARK_GRAY);

def allConditionsMet;
def highestPrice;
if IsNaN(highestPrice[1]) or allConditionsMet[1] or allConditionsMet[2] or (! isInMarketHours and resetHighOnOpenValue)
then {
    highestPrice = 0;
} else if conditionForTopWickOnly[2] and conditionForTopWickOnly[1] and ! conditionForTopWickOnly {
    highestPrice = Max(high, highestPrice[1]);
} else {
    highestPrice = highestPrice[1];
}

threshold = highestPrice * thresholdValue / 100;
sellThreshold = ( highestPrice - threshold )* ( thresholdValue + sellPriceOffsetValue ) / 100;

# Conditions for Sell
allConditionsMet = highestPrice - low > threshold and  conditionForTopWickOnly[1] and conditionForTopWickOnly and isInMarketHours;

# Sell Tracking
def sellPriceTracker;
def lastSellPrice;
def lastBuyPrice;
def buyCount;
def sellCount;
def sellingHigh;

if allConditionsMet
then {
    lastSellPrice = close + sellThreshold;
    lastBuyPrice = close;
} else {
    lastSellPrice = Double.NaN;
    lastBuyPrice = Double.NaN;
}

# Sell PriceActionIndicator Tracking
if high > sellPriceTracker[1]
then {
    sellingHigh = yes;
} else {
    sellingHigh = no;
}

sellPriceTracker = if allConditionsMet and IsNaN(sellPriceTracker[1]) then lastSellPrice else if sellingHigh[1] then Double.NaN else sellPriceTracker[1];

sellCount = if (sellingHigh and !sellingHigh[1]) then sellCount[1] + 1 else sellCount[1];

buyCount = if allConditionsMet and IsNaN(sellPriceTracker[1]) then buyCount[1] + 1 else buyCount[1];

AddChartBubble(!sellingHigh[1] and sellingHigh and sellCount > 0, sellPriceTracker[1],  "#" + sellCount + ": " + Round(sellPriceTracker[1], 2), Color.LIGHT_GREEN, yes);

# Buy Orders and Averages
def validBuy = if !IsNaN(lastBuyPrice) then 1 else 0;
def triggerCount = CompoundValue(1, triggerCount[1] + validBuy, 0);

# Sell Price Averages
def sellPriceAvgcount = CompoundValue(1, sellPriceAvgcount[1] + 1, 0);

# Plots
plot highestPriceLine = if highestPrice > 0 and highestPrice[1] == highestPrice then highestPrice else Double.NaN;
highestPriceLine.SetDefaultColor(Color.YELLOW);
highestPriceLine.SetStyle(Curve.SHORT_DASH);
highestPriceLine.SetLineWeight(1);

plot thresholdPriceLine = if !IsNaN(highestPriceLine) then highestPrice - threshold else Double.NaN;
thresholdPriceLine.SetDefaultColor(Color.YELLOW);
thresholdPriceLine.SetStyle(Curve.SHORT_DASH);
thresholdPriceLine.SetLineWeight(1);

def buySellTriggerStatus;
if (! triggerOffset or (triggerOffset and !IsNaN(sellPriceTracker[1] and !IsNaN(sellPriceTracker)))) and allConditionsMet
then {
    buySellTriggerStatus = close + threshold;
} else {
    buySellTriggerStatus = 0;
}
plot buySellTrigger = buySellTriggerStatus;

plot sellPriceLine = sellPriceTracker;
sellPriceLine.SetDefaultColor(Color.GREEN);
sellPriceLine.SetStyle(Curve.FIRM);
sellPriceLine.SetLineWeight(1);

plot highPricePlot = if allConditionsMet then highestPrice else Double.NaN;
highPricePlot.SetPaintingStrategy(PaintingStrategy.POINTS);
highPricePlot.SetLineWeight(3);
highPricePlot.SetDefaultColor(Color.YELLOW);

plot sellPricePlot = lastSellPrice;
sellPricePlot.SetPaintingStrategy(PaintingStrategy.POINTS);
sellPricePlot.SetLineWeight(3);
sellPricePlot.SetDefaultColor(Color.GREEN);

plot buyPricePlot = lastBuyPrice;
buyPricePlot.SetPaintingStrategy(PaintingStrategy.POINTS);
buyPricePlot.SetLineWeight(3);
buyPricePlot.SetDefaultColor(Color.CYAN);

plot buyArrowPlot = if !IsNaN(lastBuyPrice) then lastBuyPrice - threshold else Double.NaN;
buyArrowPlot.SetPaintingStrategy(PaintingStrategy.ARROW_UP);
buyArrowPlot.SetLineWeight(5);
buyArrowPlot.SetDefaultColor(Color.GREEN);

# Time Tracking and Metrics
def isNewDay = GetYYYYMMDD() != GetYYYYMMDD()[1];
def totalDays = CompoundValue(1, totalDays[1] + isNewDay, 1);
def lastBuyDay;
def buyDaysCount;

if sellPriceTracker {
    lastBuyDay = GetYYYYMMDD();
} else {
    lastBuyDay = lastBuyDay[1];
}
if lastBuyDay[1] != GetYYYYMMDD() and sellPriceTracker {
    buyDaysCount = buyDaysCount[1] + 1;
} else { 
    buyDaysCount = buyDaysCount[1];
}

# Labels for Metrics
def buyProfit = ( thresholdValue + sellPriceOffsetValue ) * sellCount;
def triggerProfit = thresholdValue * (buyCount + Floor((triggerCount - buyCount) / 2));

AddLabel(yes, "Triggers: " + triggerCount + 
    if triggerCount - buyCount >= 8 then ", Est. w/ Offset Gains: " + 
    triggerProfit + "%      "
    else if triggerCount < 10 then "      "
    else if triggerCount < 100 then "       "
    else if triggerCount < 1000 then "      "
    else if triggerCount < 10000 then "     "
    else if triggerCount < 100000 then "    "
    else " " , Color.CYAN);

AddLabel(yes, "Buys: " + buyCount + 
    if buyCount < 10 then "        "
    else if buyCount < 100 then "       "
    else if buyCount < 1000 then "      "
    else if buyCount < 10000 then "     "
    else if buyCount < 100000 then "    "
    else " ", Color.CYAN);

def annualFactor = if totalDays > 252 then totalDays / 252 else 1;
def profit252 = Round((252 / buyDaysCount) * buyProfit / annualFactor, 2);

def productivityScore = Round(
    (
        (buyCount / Ceil((triggerCount + 1 - buyCount) / 2)) *
        (buyProfit / 100) *
        (profit252 / 100) *
        (log(triggerCount - buyCount +1) / 10)
    ) * 100, 2
);

AddLabel(yes, "Sells: " + sellCount + ", Gained: " + 
    buyProfit + "%" +
    if sellCount < 10 then "        "
    else if sellCount < 100 then "       "
    else if sellCount < 1000 then "      "
    else if sellCount < 10000 then "     "
    else if sellCount < 100000 then "    "
    else " ", Color.LIGHT_GREEN);

AddLabel(yes, "Working Days: " + buyDaysCount + ", " + 
    "Annual Trade Gain: " + profit252 +  "%, " +
    "Score: " + productivityScore +
    if profit252 < 10 then "        " 
    else if profit252 < 100 then "       " 
    else if profit252 < 1000 then "      " 
    else if profit252 < 10000 then "     "
    else if profit252 < 100000 then "    " 
    else " ", Color.WHITE);

AddLabel(!IsNaN(sellPriceTracker), "Orders Still Open      ", Color.YELLOW);