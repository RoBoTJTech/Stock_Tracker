# ==============================
# REGIME / STRUCTURAL STRESS DETECTOR (RTH-ONLY)
# + LEVEL 5 "GET THE HELL OUT" (NO GUESSING)
# ==============================

input dropPct        = 15.0;
input volMult        = 3.0;
input avgVolLen      = 20;
input maLen          = 50;
input baseLookback   = 20;

input requireMA50    = yes;
input requireBaseLow = yes;

input useVWAPTest    = yes;   # auto-disabled on non-intraday charts
input useBottom25    = yes;

# -------- LEVEL 5 (NO-GUESS) --------
input useLevel5            = yes;
input maLenLong            = 200;
input level5BelowBothDays  = 2;     # must be below BOTH 50 & 200 for N DAYS
input level5DrawdownPct    = 20;  # must be down >= X% from 1yr peak
input level5DDLookback     = 10;   # ~1 year
input require50Falling     = yes;   # 50MA must be falling over the same N DAYS

def isIntradayChart = GetAggregationPeriod() < AggregationPeriod.DAY;

# --- RTH ONLY FILTER ---
def inRTH = SecondsFromTime(0930) >= 0 and SecondsTillTime(1600) > 0;

# Intraday series that IGNORE after-hours
def iHigh  = if inRTH then high else Double.NaN;
def iLow   = if inRTH then low else Double.NaN;
def iClose = if inRTH then close else Double.NaN;

def allowVWAP = useVWAPTest and isIntradayChart and inRTH;

# ------------------------------
# DAILY DATA (ALWAYS DAILY)
# ------------------------------
def dClose  = close(period = AggregationPeriod.DAY);
def dClose1 = close(period = AggregationPeriod.DAY)[1];
def dHigh   = high(period = AggregationPeriod.DAY);
def dLow    = low(period = AggregationPeriod.DAY);
def dVol    = volume(period = AggregationPeriod.DAY);

def dMA50    = Average(close(period = AggregationPeriod.DAY), maLen);
def dMA200   = Average(close(period = AggregationPeriod.DAY), maLenLong);
def baseLow  = Lowest(low(period = AggregationPeriod.DAY)[1], baseLookback);

# 1) Single-day drop (bad if YES)
def badDrop =
    if IsNaN(dClose1) or dClose1 == 0 then no
    else ((dClose - dClose1) / dClose1) * 100 <= -dropPct;

# 2) Volume surge (bad if YES)
def avgVol20 = Average(volume(period = AggregationPeriod.DAY), avgVolLen);
def badVol =
    if IsNaN(avgVol20) or avgVol20 == 0 then no
    else dVol >= volMult * avgVol20;

# 3) Structural break (bad if YES)
def badBreak =
    (requireMA50 and dClose < dMA50) or
    (requireBaseLow and dClose < baseLow);

# 4a) Bottom 25% daily close (bad if YES)
def badBottom25 =
    if !useBottom25 then no
    else dClose <= dLow + 0.25 * (dHigh - dLow);

# ------------------------------
# INTRADAY VWAP RECLAIM (RTH ONLY)
# ------------------------------
def vwapLine = reference VWAP();

def newRTHBar = inRTH and !inRTH[1];
def reclaimedVWAP =
    if !allowVWAP then yes
    else if newRTHBar then (iHigh > vwapLine)
    else (iHigh > vwapLine) or reclaimedVWAP[1];

def badNoReclaim = allowVWAP and !reclaimedVWAP;

# 4) No reclaim OR weak close (bad if YES)
def badReclaimOrWeakClose =
    if isIntradayChart and !inRTH then badBottom25
    else if allowVWAP then (badNoReclaim or badBottom25)
    else badBottom25;

# ------------------------------
# SCORE (0-4)
# ------------------------------
def scoreToday =
    (if badDrop then 1 else 0) +
    (if badVol then 1 else 0) +
    (if badBreak then 1 else 0) +
    (if badReclaimOrWeakClose then 1 else 0);

# ------------------------------
# LEVEL 5 (GET OUT)
# Rule (all must be true):
# 1) Below BOTH 50 & 200 for N consecutive DAYS
# 2) Down >= X% from 1-year peak
# 3) 50MA falling (optional)
# ------------------------------
def belowBoth = dClose < dMA50 and dClose < dMA200;

def belowBothDays =
    if belowBoth then belowBothDays[1] + 1 else 0;

def peakHi = Highest(high(period = AggregationPeriod.DAY), level5DDLookback);
def drawdownPct =
    if IsNaN(peakHi) or peakHi == 0 then 0
    else 100 * (dClose / peakHi - 1);

def deepDrawdown = drawdownPct <= -level5DrawdownPct;

def ma50Falling =
    if require50Falling then dMA50 < dMA50[level5BelowBothDays]
    else yes;

def level5 = useLevel5 and (belowBothDays >= level5BelowBothDays) and deepDrawdown and ma50Falling;

# ------------------------------
# REGIME OUTPUTS
# ------------------------------
def regimeBad = (scoreToday == 4) or level5;
def showDetails = (scoreToday >= 3) or level5;

def levelDisplay =
    if level5 then 5 else scoreToday;

plot RegimeOK  = if regimeBad then 0 else 1;
RegimeOK.SetLineWeight(3);

plot ScorePlot = levelDisplay;
ScorePlot.SetDefaultColor(Color.CYAN);

# ------------------------------
# LABELS (BIG, SIMPLE)
# ------------------------------
AddLabel(yes,
    if level5 then "LEVEL 5: GET OUT"
    else if scoreToday == 4 then "LEVEL 4: BAD"
    else "REGIME: OK",
    if level5 then Color.LIGHT_RED
    else if scoreToday == 4 then Color.LIGHT_RED
    else Color.GREEN
);

AddLabel(showDetails,
    "Level: " + levelDisplay +
    (if level5 then
        "  (Below50+200 " + level5BelowBothDays + "d, DD " + AsText(Round(drawdownPct,0)) + "%)"
     else ""),
    if level5 then Color.LIGHT_RED
    else if scoreToday >= 3 then Color.LIGHT_RED
    else if scoreToday == 2 then Color.YELLOW
    else Color.GREEN
);

# Keep your existing detail labels (unchanged)
AddLabel(showDetails,
    "1 Drop ≥ " + dropPct + "% (bad): " + (if badDrop then "YES" else "NO") + " ",
    if badDrop then Color.LIGHT_RED else Color.GREEN
);

AddLabel(showDetails,
    "2 Vol ≥ " + volMult + "x Avg" + avgVolLen + " (bad): " + (if badVol then "YES" else "NO") + " ",
    if badVol then Color.LIGHT_RED else Color.GREEN
);

AddLabel(showDetails,
    "3 Break MA/Base (bad): " + (if badBreak then "YES" else "NO") + " ",
    if badBreak then Color.LIGHT_RED else Color.GREEN
);

AddLabel(showDetails,
    "4 " + (if allowVWAP then "No VWAP Reclaim OR Bottom25" else "Bottom25 Only") + " (bad): " + (if badReclaimOrWeakClose then "YES" else "NO") + " ",
    if badReclaimOrWeakClose then Color.LIGHT_RED else Color.GREEN
);

AddLabel(showDetails, "50D MA: " + AsText(Round(dMA50, 2)) + "  ", Color.CYAN);
AddLabel(showDetails, "200D MA: " + AsText(Round(dMA200, 2)) + "  ", Color.CYAN);
AddLabel(showDetails, "BaseLow(" + baseLookback + "): " + AsText(Round(baseLow, 2)) + "  ", Color.CYAN);
AddLabel(showDetails and allowVWAP, "VWAP: " + AsText(Round(vwapLine, 2)) + "   ", Color.CYAN);

# ------------------------------
# SCORE ON PRICE (RTH-ONLY RANGE)  (scaled to 0..5 now)
# ------------------------------
def prHi   = HighestAll(iHigh);
def prLo   = LowestAll(iLow);
def prSpan = prHi - prLo;

def scorePrice =
    if prSpan > 0 then prLo + (prSpan * (levelDisplay / 5.0))
    else Double.NaN;

plot ScoreOnPrice =
    if inRTH then scorePrice else Double.NaN;

ScoreOnPrice.SetPaintingStrategy(PaintingStrategy.LINE);
ScoreOnPrice.SetLineWeight(2);
ScoreOnPrice.AssignValueColor(
    if level5 then Color.LIGHT_RED
    else if scoreToday >= 3 then Color.LIGHT_RED
    else if scoreToday == 2 then Color.YELLOW
    else Color.GREEN
);

# ------------------------------
# BUBBLES (intraday charts only, RTH open only)
# ------------------------------
def rthOpenBar = inRTH and SecondsFromTime(0930) == 0;

def scoreChanged = !IsNaN(scoreToday[1]) and scoreToday <> scoreToday[1];
def level5Changed = level5 <> level5[1];

def pendingChange = CompoundValue(
    1,
    if rthOpenBar then 0
    else if scoreChanged or level5Changed then 1
    else pendingChange[1],
    0
);

def yOffset = if levelDisplay >= 3 then -(prSpan * 0.03) else (prSpan * 0.03);

def bubbleCond = isIntradayChart and rthOpenBar and levelDisplay <> 0;

AddChartBubble(
    bubbleCond,
    scorePrice + yOffset,
    (if level5 then
        "L5 GET OUT DD" + AsText(Round(drawdownPct,0)) + "%"
     else if scoreToday >= 2 then
        "S" + scoreToday +
        (if badDrop then " DROP" else "") +
        (if badVol then " VOL" else "") +
        (if badBreak then " BREAK" else "") +
        (if badReclaimOrWeakClose then " WEAK" else "")
     else
        "S" + scoreToday) +
    (if pendingChange then "!" else ""),
    if level5 then Color.LIGHT_RED
    else if scoreToday >= 3 then Color.LIGHT_RED
    else if scoreToday == 2 then Color.YELLOW
    else Color.GREEN,
    levelDisplay < 3
);
