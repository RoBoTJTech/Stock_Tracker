# Order Size Target Calculater for Holding orders
# --- ACCOUNT PLAN START DATE (yyyymmdd) ---
input startDate = 20250101;
input big9CapPct = 0.20;

def daysElapsed = Max(0, DaysFromDate(startDate));
def yearsElapsed = HighestAll(Max(0, DaysFromDate(startDate))) / 365.2425;

input spyEventMode = { Twelve, Six, Four, Three, Default Two, One };
# Twelve = 12 buys/year
# Six    = 6 buys/year
# Four   = 4 buys/year
# Three  = 3 buys/year
# Two    = 2 buys/year
# One    = 1 buy/year


def spyEvents =
    if spyEventMode == spyEventMode.Twelve then 12
    else if spyEventMode == spyEventMode.Six then 6
    else if spyEventMode == spyEventMode.Four then 4
    else if spyEventMode == spyEventMode.Three then 3
    else if spyEventMode == spyEventMode.Two then 2
    else 1;

# --- SPY reference (always use SPY price, regardless of current chart) ---
def spyPrice  = close("SPY");
def spyYearly = spyPrice * spyEvents;

# assume SPY is 25% of total long-term allocation
def totalYearly = if spyYearly > 0 then spyYearly / 0.20 else 0;
def totalMonthly = totalYearly / 12;

# --- percent allocation for each of your core ETFs ---
# SPY  20%
# QQQM 15%
# SCHD 15%
# VXUS 15%
# VNQ  10%
# IBIT 10%
# PDBC  5%
# GLDM  5%
# HYG   5%

def pct =
    if  GetSymbol() == "SPY"  then 0.20
    else if GetSymbol() == "QQQM" then 0.15
    else if GetSymbol() == "SCHD" then 0.15
    else if GetSymbol() == "VXUS" then 0.15
    else if GetSymbol() == "VNQ"  then 0.10
    else if GetSymbol() == "IBIT" then 0.10
    else if GetSymbol() == "PDBC" then 0.05
    else if GetSymbol() == "GLDM" then 0.05
    else if GetSymbol() == "HYG"  then 0.05
    else 0;

# ---- current value per symbol (for total %) ----
def spyVal   = average(close("SPY"),2)   * GetQuantity(symbol = "SPY");
def qqqmVal  = average(close("QQQM"),2)  * GetQuantity(symbol = "QQQM");
def schdVal  = average(close("SCHD"),2)  * GetQuantity(symbol = "SCHD");
def vnqVal   = average(close("VNQ"),2)   * GetQuantity(symbol = "VNQ");
def vxusVal  = average(close("VXUS"),2)  * GetQuantity(symbol = "VXUS");
def ibitVal  = average(close("IBIT"),2)  * GetQuantity(symbol = "IBIT");
def pdbcVal  = average(close("PDBC"),2)  * GetQuantity(symbol = "PDBC");
def gldmVal  = average(close("GLDM"),2)  * GetQuantity(symbol = "GLDM");
def hygVal   = average(close("HYG"),2)   * GetQuantity(symbol = "HYG");
def swpLast  = average(close("SWPPX")[1],2);
def swpVal   = swpLast * GetQuantity(symbol = "SWPPX");

def totalVal =
    spyVal + qqqmVal + schdVal + vnqVal + vxusVal +
    ibitVal + pdbcVal + gldmVal + hygVal;

def spyDiff  = Round(((totalYearly * 0.20 * yearsElapsed) - (close("SPY")  * GetQuantity(symbol = "SPY")))  / close("SPY"), 0)  * close("SPY");
def qqqmDiff = Round(((totalYearly * 0.15 * yearsElapsed) - (close("QQQM") * GetQuantity(symbol = "QQQM"))) / close("QQQM"), 0) * close("QQQM");
def schdDiff = Round(((totalYearly * 0.15 * yearsElapsed) - (close("SCHD") * GetQuantity(symbol = "SCHD"))) / close("SCHD"), 0) * close("SCHD");
def vxusDiff = Round(((totalYearly * 0.15 * yearsElapsed) - (close("VXUS") * GetQuantity(symbol = "VXUS"))) / close("VXUS"), 0) * close("VXUS");
def vnqDiff  = Round(((totalYearly * 0.10 * yearsElapsed) - (close("VNQ")  * GetQuantity(symbol = "VNQ")))  / close("VNQ"), 0)  * close("VNQ");
def ibitDiff = Round(((totalYearly * 0.10 * yearsElapsed) - (close("IBIT") * GetQuantity(symbol = "IBIT"))) / close("IBIT"), 0) * close("IBIT");
def pdbcDiff = Round(((totalYearly * 0.05 * yearsElapsed) - (close("PDBC") * GetQuantity(symbol = "PDBC"))) / close("PDBC"), 0) * close("PDBC");
def gldmDiff = Round(((totalYearly * 0.05 * yearsElapsed) - (close("GLDM") * GetQuantity(symbol = "GLDM"))) / close("GLDM"), 0) * close("GLDM");
def hygDiff  = Round(((totalYearly * 0.05 * yearsElapsed) - (close("HYG")  * GetQuantity(symbol = "HYG")))  / close("HYG"), 0)  * close("HYG");

def totalDiff =
    spyDiff + qqqmDiff + schdDiff + vxusDiff + vnqDiff +
    ibitDiff + pdbcDiff + gldmDiff + hygDiff;

#def big9TargetEst = totalVal + totalDiff;
#def acctEst = big9TargetEst / big9CapPct;
def spyAcctEst  = spyVal  / (big9CapPct * 0.20);
def qqqmAcctEst = qqqmVal / (big9CapPct * 0.15);
def schdAcctEst = schdVal / (big9CapPct * 0.15);
def vxusAcctEst = vxusVal / (big9CapPct * 0.15);
def vnqAcctEst  = vnqVal  / (big9CapPct * 0.10);
def ibitAcctEst = ibitVal / (big9CapPct * 0.10);
def pdbcAcctEst = pdbcVal / (big9CapPct * 0.05);
def gldmAcctEst = gldmVal / (big9CapPct * 0.05);
def hygAcctEst  = hygVal  / (big9CapPct * 0.05);

def acctEst =
    (spyAcctEst + qqqmAcctEst + schdAcctEst + vxusAcctEst + vnqAcctEst +
     ibitAcctEst + pdbcAcctEst + gldmAcctEst + hygAcctEst) / 9;


def targetYearly  = totalYearly * pct;
def neededEvents  = if close > 0 then targetYearly / close else 0;

def diff12 = AbsValue(neededEvents - 12);
def diff6  = AbsValue(neededEvents - 6);
def diff4  = AbsValue(neededEvents - 4);
def diff3  = AbsValue(neededEvents - 3);
def diff2  = AbsValue(neededEvents - 2);
def diff1  = AbsValue(neededEvents - 1);

def minDiff =
    Min(
        Min(Min(diff12, diff6), Min(diff4, diff3)),
        Min(diff2, diff1)
    );

def bestEvents =
    if minDiff == diff12 then 12
    else if minDiff == diff6 then 6
    else if minDiff == diff4 then 4
    else if minDiff == diff3 then 3
    else if minDiff == diff2 then 2
    else 1;

# how many shares per event you really need
def rawMult = if bestEvents > 0 then neededEvents / bestEvents else 0;

# clamp to at least 1 share; round to whole shares
def sharesPerOrder = if rawMult < 1 then 1 else Round(rawMult, 0);


# ---- current chart symbol: value + P&L vs PLAN ----
def curQty  = GetQuantity();
def curCost = GetAveragePrice();
def curLast = average(close,2);
def curVal  = curLast * curQty;

# plan-to-date target for THIS symbol
def targetToDate = targetYearly * yearsElapsed;
#def goalVal      = targetToDate;
def goalVal  = totalVal * pct;
def deltaVal     = goalVal - curVal;

# % of plan funded (not % of total portfolio)
def curPct  = if totalVal > 0 then 100 * curVal / totalVal else 0;

def curPnL  = if curCost != 0 then 100 * (curLast - curCost) / curCost else 0;


# ---- SWPPX extra line on SPY chart ----
def swpQty   = GetQuantity(symbol = "SWPPX");
def swpCost  = GetAveragePrice(symbol = "SWPPX");
def swpPnL   = if swpCost != 0 then 100 * (swpLast - swpCost) / swpCost else 0;
def swpPct   = if totalVal > 0 then 100 * swpVal / totalVal else 0;


# =====================
# Labels
# =====================
def nl = GetNetLiq();
def acct =
    if !IsNaN(nl) then nl
    else acctEst;

def capVal = acct * big9CapPct;

# Use your plan number (Y) as the projection
def projectedBig9 = totalVal + totalYearly;

def trimDollars = Max(0, totalVal - capVal);
def buyRoomAfterY = Max(0, capVal - projectedBig9);

def showBuyMsg = trimDollars <= 0 and projectedBig9 <= capVal;

AddLabel(
    GetSymbol() == "SPY" and acct > 0, (if IsNaN(nl) then "Est " + AsDollars(acctEst) + " | " else "Real " + AsDollars(nl) + " | ") +
    if trimDollars > 0 then
        "BIG9 OVER " + Round(100 * totalVal / acct, 1) + "% | SELL " + AsDollars(Round(trimDollars, 0)) + "    "
    else if showBuyMsg then
        "BIG9 OK " + Round(100 * totalVal / acct, 1) + "% | BUY " + AsDollars(Round(buyRoomAfterY, 0)) + "    "
    else
        "BIG9 OK " + Round(100 * totalVal / acct, 1) + "% | HOLD    ",
    if trimDollars > 0 then Color.PINK else if showBuyMsg then Color.LIME else Color.GRAY
);

# 1) Overall totals (same on every chart)
AddLabel(
    totalYearly > 0 and GetSymbol() == "SPY",
    "Tot: A " + asDollars(totalVal + swpVal) + " Y " + AsDollars(totalYearly) +
    " | M " + AsDollars(totalMonthly) + "    ",
    Color.WHITE
);

# 2) Goal line for this ticker (target allocation + events)
# buy/sell needed to hit goal %
def adjShares = if curLast > 0 then Round(deltaVal / curLast, 0) else 0;

def adjAbs    = AbsValue(adjShares);

# --- SWPPX labels on SPY only ---
# SWPPX dollar adjustment to hit 10% goal
def swpGoalVal = Average(acct, 20) * 0.01 * (yearsElapsed + 1);
def swpNeedVal = Max(0, swpGoalVal - swpVal);


def swppxBiWeeklyRaw = swpNeedVal / 26;

def swppxBiWeekly = Max(5, Round(swppxBiWeeklyRaw / 5, 0) * 5);

def swpGoalNow = Average(acct, 20) * 0.01 * yearsElapsed;
def swpDeltaVal = swpGoalNow - swpVal;
#def swpDeltaVal  = swpGoalVal - swpVal;              # + = need more, - = too much
def swpAdjDollars = AbsValue(Round(swpDeltaVal, 0)); # whole-dollar amount




AddLabel(
    GetSymbol() == "SPY" and swpQty > 0,
    "SWPPX Tg 10% | 2wk " +
    AsDollars(swppxBiWeekly) +
    (if swpAdjDollars < 1 then " | OK"
     else if swpDeltaVal > 0 then " | +" + AsDollars(swpAdjDollars) + "    "
     else " | -" + AsDollars(swpAdjDollars) + "    "),
    Color.CYAN
);

AddLabel(
    GetSymbol() == "SPY" and swpQty > 0,
    "SWPPX Cr " +
    Round(swpPct, 1) + "% | " +
    AsDollars(swpVal) + " | PL " +
    Round(swpPnL, 1) + "%    ",
    if swpPnL > 0 then Color.LIME
    else if swpPnL < 0 then Color.ORANGE
    else Color.GRAY
);

# --- Year range (daily) ---
def yrHigh = Highest(high(period = AggregationPeriod.DAY), 252);
def yrLow  = Lowest(low(period = AggregationPeriod.DAY), 252);
def span   = if yrHigh != yrLow then (yrHigh - yrLow) else 1;

# 0 at low, 1 at high
def pos = (close - yrLow) / span;

# For buys: 0 near high, 1 near low
def sellPos  = 1 - pos;

# For sells: 0 near low, 1 near high
def buyPos = pos;

# --- Your existing “need action” flags ---
def needBuy  = adjShares > 0 and curPnL < 0;   # underweight & red
def needSell = adjShares < 0 and curPnL > 0;   # overweight & green
def strength =
    if needBuy then Round(100 * (1 - pos), 0)
    else if needSell then Round(100 * pos, 0)
    else 0;

def pale = 180;

def t0_25   = Min(Max(strength / 25, 0), 1);
def t25_50  = Min(Max((strength - 25) / 25, 0), 1);
def t50_75  = Min(Max((strength - 50) / 25, 0), 1);
def t75_100 = Min(Max((strength - 75) / 25, 0), 1);

def rr =
    if IsNaN(strength) or strength < 0 then 90
    else if strength < 25 then 255
    else if strength < 50 then 0
    else if strength < 75 then 255
    else 0;

def gg =
    if IsNaN(strength) or strength < 0 then 90
    else if strength < 25 then 255
    else if strength < 50 then Round(pale + (255 - pale) * t25_50, 0)
    else if strength < 75 then Round(pale * (1 - t50_75), 0)
    else if strength < 100 then Round(pale * (1 - t75_100), 0)
    else 0;

def bb =
    if IsNaN(strength) or strength < 0 then 90
    else if strength < 25 then Round(255 * (1 - t0_25), 0)
    else if strength < 50 then Round(pale * (1 - t25_50), 0)
    else 255;

AddLabel(
    pct > 0 and totalYearly > 0,
    "Tg " +
    (pct * 100) + "% | " +
    Round(neededEvents, 1) + " by/yr | md " +
    bestEvents +
    (if sharesPerOrder > 1 then "x" + sharesPerOrder else "") +
    (if adjAbs < 1 then " | OK    "
     else if adjShares > 0 then " | " + adjAbs + " " + AsDollars(close * adjAbs) + "    "
     else " | -" + adjAbs + " " + AsDollars(close * adjAbs) + "    "),
if needBuy then Color.GREEN
else if needSell then Color.RED
else Color.WHITE
);

AddLabel(
    curQty > 0,
    "Cr " +
    Round(curPct, 1) + "% | " +
    AsDollars(curVal) + " | PL " +
    Round(curPnL, 1) + "%    ",
    if curPnL > 0 then Color.LIME
    else if curPnL < 0 then Color.ORANGE
    else Color.GRAY
);
def skipScheduling = curPnL > 0 and adjShares < 0;

AddChartBubble(
    BarNumber() == HighestAll(BarNumber()) and skipScheduling,
    high,
    "SKIP SCHEDULING",
    Color.RED,
    yes
);

def nextBuyQty =
    if adjShares <= 0 then sharesPerOrder
    else if strength < 60 then sharesPerOrder
    else if strength < 75 then Max(sharesPerOrder, Min(adjShares, sharesPerOrder * 2))
    else if strength < 85 then Max(sharesPerOrder, Min(adjShares, sharesPerOrder * 3))
    else Max(sharesPerOrder, adjShares);


def blockMonths =
    if bestEvents == 12 then 1
    else if bestEvents == 6 then 2
    else if bestEvents == 4 then 3
    else if bestEvents == 3 then 4
    else if bestEvents == 2 then 6
    else 12;

def m = GetMonth();
def modVal = m - Floor(m / blockMonths) * blockMonths;
def isLastMonthOfSegment = modVal == 0;

def showNextBuyQty =
    isLastMonthOfSegment and GetDayOfMonth(GetYYYYMMDD()) >= 25;

def cashCatchupBuy =
    adjShares > 0 and
    pos <= 0.15 and
    curPnL >= 0;

AddChartBubble(
    BarNumber() == HighestAll(BarNumber()) and (needBuy or needSell or cashCatchupBuy),
    high,
    if cashCatchupBuy and !needBuy then
        "Cash Catch-up Buy Qty: " + nextBuyQty
    else if needBuy then
        "Balance Buy Score: " + strength
    else
        "Balance Sell Score: " + strength,
    if cashCatchupBuy then Color.CYAN else CreateColor(rr, gg, bb),
    needSell
);

AddLabel(
    showNextBuyQty and !skipScheduling,
    "Next Buy Qty: " + nextBuyQty + "    ",
    if strength >= 85 then Color.CYAN
    else if strength >= 75 then Color.LIGHT_GREEN
    else if strength >= 60 then Color.GREEN
    else Color.CYAN
);
