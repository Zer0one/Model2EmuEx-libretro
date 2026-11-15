local expanded = 0
Model2_SetWideScreen(expanded)
function Frame()
    expanded = 1 - expanded
    Model2_SetWideScreen(expanded)
end
function PostDraw()
    Frame()
end
