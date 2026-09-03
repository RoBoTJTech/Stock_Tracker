declare lower;

input detailMode = {default Off, Simple, Debug};

def barTime = GetTime();
def ymd = GetYYYYMMDD();

def dow = GetDayOfWeek(ymd);
def dom = GetDayOfMonth(ymd);
def month = GetMonth();

def daysInMonth =
    if month == 2 then 28
    else if month == 4 or month == 6 or month == 9 or month == 11 then 30
    else 31;

def isFriday = dow == 5;
def isEvenFriday = isFriday and GetWeek() % 2 == 0;
def isLastFriday = isFriday and dom > daysInMonth - 7;

def firstSeenBarTime = CompoundValue(1, firstSeenBarTime[1], barTime);

def armed = CompoundValue(1,
    if armed[1] then 1
    else if barTime <> firstSeenBarTime then 1
    else 0,
    0
);

def cancelNow =
    (SecondsFromTime(1554) >= 0 and dow <= 4)
    or (SecondsTillTime(1554) >= 0 and SecondsFromTime(1400) >= 0 and dow >=5 );

plot cancelOrder =
    if armed and cancelNow then
        if isLastFriday then 7
        else if isEvenFriday then 6
        else dow
    else 0;

cancelOrder.SetPaintingStrategy(PaintingStrategy.HISTOGRAM);
cancelOrder.SetLineWeight(3);

AddLabel(detailMode == detailMode.Debug, "dow=" + dow, Color.WHITE);
AddLabel(detailMode == detailMode.Debug, "dom=" + dom, Color.WHITE);
AddLabel(detailMode == detailMode.Debug, "daysInMonth=" + daysInMonth, Color.WHITE);
AddLabel(detailMode == detailMode.Debug, "isFriday=" + isFriday, Color.WHITE);
AddLabel(detailMode != detailMode.Off, "isEvenFriday=" + isEvenFriday, Color.YELLOW);
AddLabel(detailMode != detailMode.Off, "isLastFriday=" + isLastFriday, Color.YELLOW);
AddLabel(detailMode == detailMode.Debug, "armed=" + armed, Color.CYAN);
AddLabel(detailMode == detailMode.Debug, "cancelNow=" + cancelNow, Color.ORANGE);
AddLabel(detailMode != detailMode.Off, "cancelOrder=" + cancelOrder, Color.GREEN);
