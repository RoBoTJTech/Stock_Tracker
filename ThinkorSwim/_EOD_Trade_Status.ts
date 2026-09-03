#Scan filter for ETFs
# ---- ETF junk / decay filter for WEEKLY scan (uses prior bar [1]) ----
input minYears         = 3;      # history window in years
input minOfAllTimeHigh = 0.40;   # must be >= 40% of all-time high
input spikePct         = 0.08;   # weekly bar > 8% range = spike
input maxSpikes        = 10;     # max spikes in last 52 weeks
input useLongSlope     = yes;    # extra long-term decay check
input longSlopeYears   = 5;      # window for extra slope check
input volThresh        = 0.05;   # ATR% threshold for "high-vol / maybe leveraged"
input blockHighVol     = yes;    # if yes, leverage filter is part of scan
input minDollarVol     = 10000000;  # 50-day $ volume floor (e.g. $10M)
input showDebug        = no;    # turn ALL labels on/off


def barsPerYear = 52;
def barsBack    = minYears * barsPerYear;
def longBars    = longSlopeYears * barsPerYear;

# --- basic history check: use bar[1] as reference ---
def enoughHistory = !IsNaN(close[barsBack + 1]);

# 1) Higher than N years ago & above 40-week MA, all on [1]
def longTermUp =
    enoughHistory and
    close[1] > close[barsBack + 1] and
    close[1] > Average(close[1], 40);

# 2) Positive slope over minYears, ending at bar[1]
def slopeN =
    if enoughHistory
    then LinearRegressionSlope(close[1], barsBack)
    else 0;
def trendOK = slopeN > 0;

# 3) Extra long-term decay check (optional), also on [1]
def slopeLong =
    if useLongSlope and !IsNaN(close[longBars + 1])
    then LinearRegressionSlope(close[1], longBars)
    else slopeN;
def trendLongOK = slopeLong > 0;

# 4) Not a crazy spiky product (use [1] bar only)
def spike      = (high[1] - low[1]) / close[1] > spikePct;
def spikeCount = Sum(spike, 52);
def volOK      = spikeCount < maxSpikes;

# 5) Not "cratered forever" vs all-time high (history based on [1])
def allTimeHigh = HighestAll(high[1]);
def notCratered = if allTimeHigh != 0
                  then close[1] >= minOfAllTimeHigh * allTimeHigh
                  else no;

# 6) 50-day dollar volume filter (using prior bar [1])
def avgVol50    = Average(volume[1], 50);
def dollarVol50 = avgVol50 * close[1];
def dollarVolOK = dollarVol50 >= minDollarVol;

# --- High-volatility / likely leveraged flag (daily-style logic on [1]) ---
def atr    = Average(TrueRange(high[1], close[2], low[1]), 60);
def volPct = atr / close[1];
def likelyLeveraged = volPct > volThresh;

# leverage filter toggle
def leveragePass = if blockHighVol then !likelyLeveraged else 1;

# ---- MAIN SCAN PLOT (INCLUDES LEVERAGE + $VOL FILTER, all based on [1]) ----
plot scan =
    longTermUp and
    trendOK and
    trendLongOK and
    volOK and
    notCratered and
    dollarVolOK and
    leveragePass;

# ---- DEBUG LABELS FOR WEEKLY ETF FILTER ----
AddLabel(
    showDebug,
    "Trade: " +
    (if scan then "YES" else "NO") +
    (if blockHighVol and likelyLeveraged then " (LevBlocked)" else "") + " ",
    if scan then Color.GREEN else Color.RED
);

AddLabel(
    showDebug and !scan,
    "History (" + minYears + "y): " +
    (if enoughHistory then "OK" else "SHORT") + " ",
    if enoughHistory then Color.GREEN else Color.RED
);

AddLabel(
    showDebug and !scan,
    "LongTermUp: " +
    (if longTermUp then "YES" else "NO") +
    "  (Close[1] vs " + minYears + "y ago & >40WMA)" + " ",
    if longTermUp then Color.GREEN else Color.RED
);

AddLabel(
    showDebug and !scan,
    "Slope " + minYears + "y: " + Round(slopeN, 5) +
    "  trendOK=" + (if trendOK then "YES" else "NO") + "  ",
    if trendOK then Color.GREEN else Color.RED
);

AddLabel(
    showDebug and !scan,
    "Slope " + longSlopeYears + "y: " + Round(slopeLong, 5) +
    "  longOK=" + (if trendLongOK then "YES" else "NO") + "  ",
    if trendLongOK then Color.GREEN else Color.RED
);

AddLabel(
    showDebug and !scan,
    "Spikes(52w): " + spikeCount +
    "  volOK=" + (if volOK then "YES" else "NO") + "  ",
    if volOK then Color.GREEN else Color.RED
);

AddLabel(
    showDebug and !scan,
    "50d $Vol: " +
    AsText(Round(dollarVol50 / 1000000, 1)) + "M " +
    (if dollarVolOK then "OK" else "LOW") + "  ",
    if dollarVolOK then Color.GREEN else Color.RED
);

def athRatio = if allTimeHigh != 0 then close[1] / allTimeHigh else 0;

AddLabel(
    showDebug and !scan,
    "ATH ratio: " + AsText(Round(athRatio * 100, 1)) + "%  " +
    "min=" + AsText(Round(minOfAllTimeHigh * 100, 0)) + "%" +
    "  cratered=" + (if notCratered then "NO" else "YES") + "  ",
    if notCratered then Color.GREEN else Color.RED
);

# --- Leverage / vol label BEFORE SCAN PASS ---
AddLabel(
    showDebug and !scan,
    if likelyLeveraged
    then "High-Vol / Maybe Leveraged "
    else "Normal Vol ",
    if likelyLeveraged then Color.RED else Color.GREEN
);
