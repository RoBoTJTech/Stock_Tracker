#Account status for account chart
def bn = BarNumber();
input big9CapPct = 20; # use 20, not .20

def spyVal  = Average(close("SPY"), 2)  * GetQuantity(symbol = "SPY");
def qqqmVal = Average(close("QQQM"), 2) * GetQuantity(symbol = "QQQM");
def schdVal = Average(close("SCHD"), 2) * GetQuantity(symbol = "SCHD");
def vxusVal = Average(close("VXUS"), 2) * GetQuantity(symbol = "VXUS");
def vnqVal  = Average(close("VNQ"), 2)  * GetQuantity(symbol = "VNQ");
def ibitVal = Average(close("IBIT"), 2) * GetQuantity(symbol = "IBIT");
def pdbcVal = Average(close("PDBC"), 2) * GetQuantity(symbol = "PDBC");
def gldmVal = Average(close("GLDM"), 2) * GetQuantity(symbol = "GLDM");
def hygVal  = Average(close("HYG"), 2)  * GetQuantity(symbol = "HYG");

def netLiqRaw = GetNetLiq();


def spyAcctEst  = spyVal  / ((big9CapPct / 100) * 0.20);

def qqqmAcctEst = qqqmVal / ((big9CapPct / 100) * 0.15);

def schdAcctEst = schdVal / ((big9CapPct / 100) * 0.15);

def vxusAcctEst = vxusVal / ((big9CapPct / 100) * 0.15);

def vnqAcctEst  = vnqVal  / ((big9CapPct / 100) * 0.10);

def ibitAcctEst = ibitVal / ((big9CapPct / 100) * 0.10);

def pdbcAcctEst = pdbcVal / ((big9CapPct / 100) * 0.05);

def gldmAcctEst = gldmVal / ((big9CapPct / 100) * 0.05);

def hygAcctEst  = hygVal  / ((big9CapPct / 100) * 0.05);

def netLiqEst =
    (spyAcctEst + qqqmAcctEst + schdAcctEst + vxusAcctEst + vnqAcctEst + ibitAcctEst + pdbcAcctEst + gldmAcctEst + hygAcctEst) / 9;

#def big9Value =
#    spyVal + qqqmVal + schdVal + vxusVal + vnqVal +
#    ibitVal + pdbcVal + gldmVal + hygVal;
#def netLiqEst =
#    if big9CapPct > 0 then big9Value / (big9CapPct / 100)
#    else Double.NaN;

def netLiq =
    if IsNaN(netLiqRaw) then netLiqEst
    else netLiqRaw;

def freeCashRaw = GetTotalCash();

def freeCash =
    if IsNaN(freeCashRaw) then netLiqEst * (.20 + Average(close("VIX"),10) /100)
    else freeCashRaw;


def freeCashAvg = Average(freeCash, 2);
def vix = Highest(close("vix"),10); #Average(close("vix"), 1);

def hiLiq = HighestAll(netLiq);
def hiClose = HighestAll(close);
def loClose = LowestAll(close);
def DWCFIndex = close("$DWCF");
def hiDWCF = HighestAll(DWCFIndex);
def loDWCF = LowestAll(DWCFIndex);
def hiDWCFBar = HighestAll(if DWCFIndex == hiDWCF then bn else 0);
def loDWCFBar = HighestAll(if DWCFIndex == loDWCF then bn else 0);
def scale = hiClose / hiLiq;
def DWCFscale = hiClose / hiDWCF;
plot cash = freeCash / 3 * scale + (loClose / 3);
plot totalValue = netLiq * scale + (loClose / 2);
cash.SetDefaultColor(Color.CYAN);
totalValue.SetDefaultColor(Color.YELLOW);

plot DWCF = DWCFIndex * DWCFscale  + (loClose / 1);
DWCF.SetDefaultColor(Color.MAGENTA);
def oldestBN = HighestAll(bn);
def oldestClose = GetValue(close, oldestBN);
def firstValidBN =
    CompoundValue(1,
        if IsNaN(firstValidBN[1]) and netLiq > 0
        then BarNumber()
        else firstValidBN[1],
    Double.NaN);


def oldestLiq =
    if !IsNaN(firstValidBN)
    then GetValue(netLiq, HighestAll(BarNumber()) - firstValidBN)
    else Double.NaN;


def pctStock = if oldestClose != 0 then (close / oldestClose - 1) else 0;
def pctLiq   = if oldestLiq   != 0 then (netLiq / oldestLiq   - 1) else 0;

def tradePriceBase = (Ceil(freeCashAvg / 5000) * 50) * 2;
def tradePricePower = Power(tradePriceBase, 1.05);
def tradePrice = if tradePricePower > 100
                        then Floor(tradePricePower / 100) * 100
                        else tradePriceBase;

def pale = 180;

def t0_10    = Min(Max(tradePrice / 1000, 0), 1);
def t10_50   = Min(Max((tradePrice - 1000) / 4000, 0), 1);
def t50_100  = Min(Max((tradePrice - 5000) / 5000, 0), 1);
def t100_500 = Min(Max((tradePrice - 10000) / 40000, 0), 1);

def r =
    if IsNaN(tradePrice) or tradePrice <= 0 then 90
    else if tradePrice < 1000 then 255                          # white->yellow keeps r=255
    else if tradePrice < 5000 then 0                            # green band
    else if tradePrice < 10000 then 255                         # magenta band
    else if tradePrice < 50000 then 0                           # blue band
    else 0;

def g =
    if IsNaN(tradePrice) or tradePrice <= 0 then 90
    else if tradePrice < 1000 then 255                          # white->yellow keeps g=255
    else if tradePrice < 5000 then 255                          # green band stays g=255
    else if tradePrice < 10000 then
        Round(pale * (1 - t50_100), 0)                               # pale->0 (pale magenta -> magenta)
    else if tradePrice < 50000 then
        Round(pale * (1 - t100_500), 0)                              # pale->0 (pale blue -> blue)
    else 0;

def b =
    if IsNaN(tradePrice) or tradePrice <= 0 then 90
    else if tradePrice < 1000 then
        Round(255 * (1 - t0_10), 0)                                  # 255->0 (white->yellow)
    else if tradePrice < 5000 then
        Round(pale * (1 - t10_50), 0)                                # pale->0 (pale green -> green)
    else if tradePrice < 50000 then
        255                                                          # magenta + blue both keep b=255
    else 255;

def etfTradePrice = tradePrice/4;

def etf_t0_10    = Min(Max(etfTradePrice / 1000, 0), 1);
def etf_t10_50   = Min(Max((etfTradePrice - 1000) / 4000, 0), 1);
def etf_t50_100  = Min(Max((etfTradePrice - 5000) / 5000, 0), 1);
def etf_t100_500 = Min(Max((etfTradePrice - 10000) / 40000, 0), 1);

def etf_r =
    if IsNaN(tradePrice) or tradePrice <= 0 then 90
    else if etfTradePrice < 1000 then 255                          # white->yellow keeps r=255
    else if etfTradePrice < 5000 then 0                            # green band
    else if etfTradePrice < 10000 then 255                         # magenta band
    else if etfTradePrice < 50000 then 0                           # blue band
    else 0;

def etf_g =
    if IsNaN(tradePrice) or tradePrice <= 0 then 90
    else if etfTradePrice < 1000 then 255                          # white->yellow keeps g=255
    else if etfTradePrice < 5000 then 255                          # green band stays g=255
    else if etfTradePrice < 10000 then
        Round(pale * (1 - etf_t50_100), 0)                               # pale->0 (pale magenta -> magenta)
    else if etfTradePrice < 50000 then
        Round(pale * (1 - etf_t100_500), 0)                              # pale->0 (pale blue -> blue)
    else 0;

def etf_b =
    if IsNaN(tradePrice) or tradePrice <= 0 then 90
    else if etfTradePrice < 1000 then
        Round(255 * (1 - etf_t0_10), 0)                                  # 255->0 (white->yellow)
    else if etfTradePrice < 5000 then
        Round(pale * (1 - etf_t10_50), 0)                                # pale->0 (pale green -> green)
    else if etfTradePrice < 50000 then
        255                                                          # magenta + blue both keep b=255
    else 255;

AddLabel(
    yes,
    "VIX: " + vix + " | Trade Stock @ " + AsDollars(tradePrice) + "  ",
    CreateColor(
        r,
        g,
        b
    )
);

AddLabel(
    yes,
    "Trade ETF @ " + AsDollars(round(etfTradePrice)) + "  ",
    CreateColor(
        etf_r,
        etf_g,
        etf_b
    )
);

AddLabel(
    yes, (if IsNaN(freeCashRaw) then "Est. " else "") +
    "Free Cash: " + AsDollars(freeCash) +
    "  ", COLOR.CYAN
);

# ===== 4 bubbles: NetLiq hi/lo and FreeCash hi/lo =====
def loLiq   = LowestAll(netLiq);
def hiCash  = HighestAll(freeCash);
def loCash  = LowestAll(freeCash);

def hiLiqBar = HighestAll(if netLiq  == hiLiq  then bn else 0);
def loLiqBar = HighestAll(if netLiq  == loLiq  then bn else 0);
def hiCashBar= HighestAll(if freeCash== hiCash then bn else 0);
def loCashBar= HighestAll(if freeCash== loCash then bn else 0);

AddChartBubble(bn == hiLiqBar,  totalValue, "Hi: " + Round(hiLiq, 2),  Color.YELLOW, yes);
AddChartBubble(bn == loLiqBar,  totalValue, "Lo: " + Round(loLiq, 2),  Color.YELLOW, no);
AddChartBubble(bn == hiCashBar,  cash,       "Hi: " + Round(hiCash, 2), Color.CYAN, yes);
AddChartBubble(bn == loCashBar,  cash,       "Lo: " + Round(loCash, 2), Color.CYAN, no);

# % gain for composite (from first visible bar)
def DWCFFirst = GetValue(DWCFIndex, HighestAll(BarNumber()) - 1);
def pctComp   = if DWCFFirst != 0 then (DWCFIndex / DWCFFirst - 1) else 0;

# Colored % labels with current price: ticker=orange, NetLiq=yellow, Composite=magenta
AddLabel(yes, (if IsNaN(netLiqRaw) then "Est. " else "") +"NetLiq: " + AsPercent(pctLiq) + "  " + AsDollars(netLiq) + "   ", Color.YELLOW);
AddLabel(yes, GetSymbol() + ": " + AsPercent(pctStock) + "  " + AsDollars(close) + "   ", Color.ORANGE);
AddLabel(yes, "$DWCF: " + AsPercent(pctComp) + "  " + AsDollars(DWCFIndex) + "   ", Color.MAGENTA);




