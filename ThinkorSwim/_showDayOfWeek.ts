def newDay = GetYYYYMMDD() <> GetYYYYMMDD()[1];
def balance = AccountNetLiq();
AddChartBubble(
    newDay,
    low,
    balance + " " +
    if GetDayOfWeek(GetYYYYMMDD()) == 1 then "Mon"
    else if GetDayOfWeek(GetYYYYMMDD()) == 2 then "Tue"
    else if GetDayOfWeek(GetYYYYMMDD()) == 3 then "Wed"
    else if GetDayOfWeek(GetYYYYMMDD()) == 4 then "Thu"
    else if GetDayOfWeek(GetYYYYMMDD()) == 5 then "Fri"
    else if GetDayOfWeek(GetYYYYMMDD()) == 6 then "Sat"
    else "Sun",
    Color.WHITE,
    no
);


