def pos = GetQuantity();
def ytd = GetAggregatedPL();

# Notes cannot be accessed in ThinkScript → ignore or handle manually

def needOrder =
    (pos == 0 and ytd != 0) or
    (IsNaN(pos) and IsNaN(ytd));

plot scan = if needOrder then 1 else 0;
