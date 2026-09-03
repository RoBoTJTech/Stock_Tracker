# Scan filter for Intraday
# Daily SMA settings (ensure these are consistent with your chart settings)
input length1 = 50;
input length2 = 200;

# Define the periods for slope calculation
input slopePeriodShort = 10;
input timeoutDays = 10;

input showDetails = no;
input conditionOnly = no;

# Calculate SMAs
def EMAShort;
def SMALong;
def EMAVolume;
def dayOpen;
def dayClose;
if ! conditionOnly
then {
    EMAVolume = MovAvgExponential(volume(period = AggregationPeriod.DAY), length1);
    EMAShort = MovAvgExponential(close(period = AggregationPeriod.DAY), length1);
    SMALong = SimpleMovingAvg(close(period = AggregationPeriod.DAY), length2);
    dayOpen = open(period = AggregationPeriod.DAY);
    dayClose = close(period = AggregationPeriod.DAY);
}
else {
    EMAVolume = MovAvgExponential(volume, length1);
    EMAShort = MovAvgExponential(close, length1);
    SMALong = SimpleMovingAvg(close, length2);
    dayOpen = open;
    dayClose = close;
}

# Calculate slopes for the last period and the previous period for 50-day SMA
def slopeSMAShort_last_period = (EMAShort[0] - EMAShort[slopePeriodShort - 1]) / slopePeriodShort;
def slopeSMAShort_prev_period = (EMAShort[slopePeriodShort] - EMAShort[2 * slopePeriodShort - 1]) / slopePeriodShort;

# Calculate slopes for the last period and the previous period for 200-day SMA
def slopeSMALong_last_period = (SMALong[0] - SMALong[slopePeriodShort - 1]) / slopePeriodShort;
def slopeSMALong_prev_period = (SMALong[slopePeriodShort] - SMALong[2 * slopePeriodShort - 1]) / slopePeriodShort;

# Plot SMAs
plot DailyEMAShort = EMAShort;
DailyEMAShort.SetDefaultColor(Color.CYAN);
plot DailySMALong = SMALong;
DailySMALong.SetDefaultColor(Color.MAGENTA);

# Conditions for swing trading
def c1 = dayClose > EMAShort * 1.03;
def c2 = EMAShort > SMALong * 1.03;
def c3 = slopeSMAShort_last_period > slopeSMAShort_prev_period;
def c4 = slopeSMALong_last_period > slopeSMALong_prev_period;
def c5 = slopeSMAShort_last_period > slopeSMALong_last_period * 1.0005;
def c6 = EMAVolume[1] >= EMAVolume[slopePeriodShort - 1];
def c7 = !(dayOpen < dayOpen[1] and dayOpen[1] < dayOpen[2] and dayOpen[2] < dayOpen[3]);

# Assign conditions to labels
def tradeCondition = c1 and c2 and c3 and c4 and c5 and c6 and c7;


# Plot to indicate trade condition met
plot Trade = if tradeCondition then 1 else 0;


# === ACTIVE STREAK (past 10 bars) ===
def activeStreak = Highest(tradeCondition, timeoutDays) > 0;
plot StreakLine = if activeStreak then 2 else Double.NaN;
StreakLine.SetDefaultColor(Color.YELLOW);
StreakLine.SetLineWeight(2);

# === STREAK TRACKING ===
def streakStart = activeStreak and !activeStreak[1];
def streakEnd = !activeStreak and activeStreak[1];

def barCount = if activeStreak then barCount[1] + 1 else 0;

def entryLow = if streakStart then low else if activeStreak then entryLow[1] else Double.NaN;
def peakHigh = if streakStart then high else if activeStreak then Max(peakHigh[1], high) else Double.NaN;

def gainPct = if streakEnd and entryLow[1] > 0 then
                 100 * (peakHigh[1] - entryLow[1]) / entryLow[1]
              else Double.NaN;

def extPct = if streakEnd and EMAShort[1] > 0 then
                 100 * ((peakHigh[1] / EMAShort[1]) - 1)
             else 0;

def extSum   = TotalSum(extPct);
def extCount = TotalSum(if extPct > 0 then 1 else 0);
def avgExt   = if extCount > 0 then extSum / extCount else 10;

def currentExt = if tradeCondition and EMAShort > 0 then
                     100 * ((peakHigh / EMAShort) - 1)
                 else 0;

def notLate = currentExt <= avgExt;

# === STATS ===
def gainSum = TotalSum(if !IsNaN(gainPct) then gainPct else 0);
def gainCount = TotalSum(if !IsNaN(gainPct) then 1 else 0);
def avgGain = if gainCount > 0 then gainSum / gainCount else Double.NaN;

def currentGain = if tradeCondition and entryLow > 0 then
                     100 * (peakHigh - entryLow) / entryLow
                  else Double.NaN;

def safeAvgGain = if IsNaN(avgGain) then 0 else avgGain;
def safeCurrentGain = if IsNaN(currentGain) then 0 else currentGain;
#def activelyTradeState = safeCurrentGain <= safeAvgGain and trade;
def activelyTradeState = safeCurrentGain <= safeAvgGain and currentExt <= avgExt and trade;

plot activelyTrade = if activelyTradeState then 1 else 0;

AddLabel(
    !conditionOnly,
    if tradeCondition and activelyTradeState then "Trade" else "Do Not Trade",
    if tradeCondition and activelyTradeState then Color.GREEN else Color.LIGHT_RED
);


def sinceTradeTrue =
    if tradeCondition then 0
    else sinceTradeTrue[1] + 1;

def daysLeft = timeoutDays - sinceTradeTrue;

AddLabel(
    !conditionOnly and !tradeCondition and sinceTradeTrue > 0 and daysLeft >= 0,
    "Dump in " + daysLeft + " day(s) ",
    Color.YELLOW
);


# === BUBBLES ===
AddChartBubble(
    streakEnd and showDetails,
    peakHigh[1],
    "S:" + AsDollars(entryLow[1]) + " H:" + AsDollars(peakHigh[1]) + " +" + Round(gainPct, 1) + "%",
    Color.BLUE,
    yes
);

# === CURRENT STREAK GAIN LABEL ===

AddLabel(!conditionOnly, "Average Streak Gain: " + AsText(Round(safeAvgGain, 1)) + "%", Color.CYAN);
AddLabel(!conditionOnly, "Avg 50EMA Ext: " + AsText(Round(avgExt, 1)) + "%", Color.CYAN);

AddLabel(
    !conditionOnly,
    "Current Streak Gain: " + AsText(Round(safeCurrentGain, 1)) + "%",
    if safeCurrentGain <= safeAvgGain then Color.GREEN else Color.RED
);
AddLabel(
    !conditionOnly,
    "Current 50EMA Ext: " + AsText(Round(currentExt, 1)) + "%",
    if currentExt <= avgExt then Color.GREEN else Color.RED
);


# Individual condition labels
AddLabel(!conditionOnly and showDetails, "MA (Close > 50d): " + (if c1 then "Met    " else "Not Met    "), if c1 then Color.LIGHT_GREEN else Color.LIGHT_RED);

AddLabel(!conditionOnly and showDetails, "MA (50d > 200d): " + (if c2 then "Met    " else "Not Met    "), if c2 then Color.LIGHT_GREEN else Color.LIGHT_RED);

AddLabel(!conditionOnly and showDetails, "MA (50d slope increasing): " + (if c3 then "Met    " else "Not Met    "), if c3 then Color.LIGHT_GREEN else Color.LIGHT_RED);

AddLabel(!conditionOnly and showDetails, "MA (200d slope increasing): " + (if c4 then "Met    " else "Not Met    "), if c4 then Color.LIGHT_GREEN else Color.LIGHT_RED);

AddLabel(!conditionOnly and showDetails, "MA (50d slope > 200d slope by 0.05%): " + (if c5 then "Met    " else "Not Met    "), if c5 then Color.LIGHT_GREEN else Color.LIGHT_RED);

AddLabel(!conditionOnly and showDetails, "MA (Volume Incress): " + (if c6 then "Met    " else "Not Met    "), if c6 then Color.LIGHT_GREEN else Color.LIGHT_RED);

AddLabel(!conditionOnly and showDetails, "Close: " + dayClose, Color.WHITE);
AddLabel(!conditionOnly and showDetails, "50d MA: " + EMAShort, Color.WHITE);
AddLabel(!conditionOnly and showDetails, "200d MA: " + SMALong, Color.WHITE);
AddLabel(!conditionOnly and showDetails, "Volume MA: " + Round(EMAVolume, 0), Color.WHITE);
AddLabel(!conditionOnly and showDetails, "50d last period slope: " + slopeSMAShort_last_period, Color.WHITE);
AddLabel(!conditionOnly and showDetails, "50d prev period slope: " + slopeSMAShort_prev_period, Color.WHITE);
AddLabel(!conditionOnly and showDetails, "200d last period slope: " + slopeSMALong_last_period, Color.WHITE);
AddLabel(!conditionOnly and showDetails, "200d prev period slope: " + slopeSMALong_prev_period + " " + GetYYYYMMDD(), Color.WHITE);


