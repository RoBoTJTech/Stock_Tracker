# ==============================
# MAX TRADE SIZE FROM DAILY ADV$
# MaxTrade$ = (AvgDailyDollarVol(5) / 78) * %
# ==============================
input maxPercentToBuy = .1;

def dClose1 = close(period = AggregationPeriod.DAY)[1];
def dVol1   = volume(period = AggregationPeriod.DAY)[1];

def dDol1 =
    if IsNaN(dClose1) or IsNaN(dVol1) then Double.NaN
    else dClose1 * dVol1;

def advDay5 = Average(dDol1, 5);
def maxTradeDollars = if IsNaN(advDay5) then Double.NaN else advDay5 * (maxPercentToBuy / 100);

def px = close;
def maxShares =
    if IsNaN(maxTradeDollars) or IsNaN(px) or px <= 0 then 0
    else Floor(maxTradeDollars / px);

def pale = 180;

def t0_10    = Min(Max(maxTradeDollars / 1000, 0), 1);
def t10_50   = Min(Max((maxTradeDollars - 1000) / 4000, 0), 1);
def t50_100  = Min(Max((maxTradeDollars - 5000) / 5000, 0), 1);
def t100_500 = Min(Max((maxTradeDollars - 10000) / 40000, 0), 1);

def r =
    if IsNaN(maxTradeDollars) or maxTradeDollars <= 0 then 90
    else if maxTradeDollars < 1000 then 255                          # white->yellow keeps r=255
    else if maxTradeDollars < 5000 then 0                            # green band
    else if maxTradeDollars < 10000 then 255                         # magenta band
    else if maxTradeDollars < 50000 then 0                           # blue band
    else 0;

def g =
    if IsNaN(maxTradeDollars) or maxTradeDollars <= 0 then 90
    else if maxTradeDollars < 1000 then 255                          # white->yellow keeps g=255
    else if maxTradeDollars < 5000 then 255                          # green band stays g=255
    else if maxTradeDollars < 10000 then
        Round(pale * (1 - t50_100), 0)                               # pale->0 (pale magenta -> magenta)
    else if maxTradeDollars < 50000 then
        Round(pale * (1 - t100_500), 0)                              # pale->0 (pale blue -> blue)
    else 0;

def b =
    if IsNaN(maxTradeDollars) or maxTradeDollars <= 0 then 90
    else if maxTradeDollars < 1000 then
        Round(255 * (1 - t0_10), 0)                                  # 255->0 (white->yellow)
    else if maxTradeDollars < 5000 then
        Round(pale * (1 - t10_50), 0)                                # pale->0 (pale green -> green)
    else if maxTradeDollars < 50000 then
        255                                                          # magenta + blue both keep b=255
    else 255;

# avoid any "black" looking label: don't use GRAY, and don't print NaN labels
#AddLabel(!IsNaN(advDay5),        "ADV$ day(5): " + AsDollars(advDay5) + "  ", Color.CYAN);
#AddLabel(!IsNaN(adv5m),          "ADV$/5m: "     + AsDollars(adv5m)   + "  ", Color.LIGHT_GRAY);
AddLabel(!IsNaN(maxTradeDollars),"Max Spend (" + maxPercentToBuy + "%): "  + AsDollars(maxTradeDollars) + "  ", 
    CreateColor(
        r,
        g,
        b
    )
);
