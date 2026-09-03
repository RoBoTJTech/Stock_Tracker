input eventMode = { default Twelve, Six, Four, Three, Two, One };

def m = GetMonth();  # 1..12

def segIndex =
    if eventMode == eventMode.Twelve then m                                  # 12 blocks (1 mo)
    else if eventMode == eventMode.Six then RoundDown((m - 1) / 2, 0) + 1    # 6 blocks (2 mo)
    else if eventMode == eventMode.Four then RoundDown((m - 1) / 3, 0) + 1   # 4 blocks (3 mo)
    else if eventMode == eventMode.Three then RoundDown((m - 1) / 4, 0) + 1  # 3 blocks (4 mo)
    else if eventMode == eventMode.Two then RoundDown((m - 1) / 6, 0) + 1    # 2 blocks (6 mo)
    else 1;                                                                  # 1 block (12 mo)

# --- raw TTM PivotLow (exact bar) ---
def yr = Floor(GetYYYYMMDD() / 10000);
def latestYr = Floor(HighestAll(GetYYYYMMDD()) / 10000);

def newBlock = !IsNaN(segIndex[1]) and segIndex[1] != segIndex;

def MA50  = Average(close, 50);
def MA200 = Average(close, 200);

def haClose = (open + high + low + close) / 4;
def haOpen  = CompoundValue(1, (haOpen[1] + haClose[1]) / 2, (open + close) / 2);

def haGreen = haClose > haOpen;
def haRed   = haClose < haOpen;

# 2 red, then 2 green (signal on 2nd green)
def buyPoint1 = haRed[4] and haRed[3] and haRed[2] and haGreen[1];
def buyPoint2 = MA50[1] > MA200[1] and high[1] > MA50 and haRed[2] and haGreen[1];
def buyPoint3 = MA50[1] > MA200[1] and high[1] > MA50 and haGreen[5] and haGreen[4] and haGreen[3] and haGreen[2] and haGreen[1]; #and ewBlock[1]
def buyPoint = buyPoint1 or buyPoint2 or buyPoint3;

# --- only FIRST PivotLow in each active event window per year ---
def seenThisBlock =
    CompoundValue( 
        1,
        if newBlock then 0
        else if buyPoint and seenThisBlock[1] == 0 then 1
        else seenThisBlock[1],
        0
    );

# plot at LOW so arrow sits under the candle
plot BuySlot =
    if buyPoint and BarNumber() != 1 and seenThisBlock[1] == 0
    then low
    else Double.NaN;


BuySlot.SetPaintingStrategy(PaintingStrategy.ARROW_UP);
BuySlot.SetLineWeight(3);

BuySlot.AssignValueColor(
    if segIndex[1] == 1 then Color.CYAN
    else if segIndex[1] == 2 then Color.MAGENTA
    else if segIndex[1] == 3 then Color.YELLOW
    else if segIndex[1] == 4 then Color.ORANGE
    else if segIndex[1] == 5 then Color.PINK
    else if segIndex[1] == 6 then Color.LIGHT_GREEN
    else if segIndex[1] == 7 then Color.LIGHT_RED
    else if segIndex[1] == 8 then Color.LIGHT_GRAY
    else if segIndex[1] == 9 then Color.BLUE
    else if segIndex[1] == 10 then Color.GREEN
    else if segIndex[1] == 11 then Color.RED
    else if segIndex[1] == 12 then Color.DARK_ORANGE
    else Color.WHITE
);

AddChartBubble(BarNumber() == HighestAll(BarNumber()) && seenThisBlock == 0, high, "Waiting", Color.YELLOW, yes);

AddVerticalLine(newBlock, "B" + segIndex[1], Color.DARK_RED);



def blockMonths =
    if eventMode == eventMode.Twelve then 1
    else if eventMode == eventMode.Six then 2
    else if eventMode == eventMode.Four then 3
    else if eventMode == eventMode.Three then 4
    else if eventMode == eventMode.Two then 6
    else 12;

def modVal = m - Floor(m / blockMonths) * blockMonths;  # modulo
def isLastMonthOfSegment = modVal == 0;
def nearEnd = isLastMonthOfSegment and seenThisBlock[3] and GetDayOfMonth(GetYYYYMMDD()) >= 25;
AddChartBubble(BarNumber() == HighestAll(BarNumber()) && nearEnd, high, "Setup next order", Color.CYAN, yes);
