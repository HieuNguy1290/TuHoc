"""Presentation-only Tkinter line/dot chart; does not change persistence."""
def draw_line_dot(canvas, values, labels, *, line='#5269E8', dot='#5269E8', grid='#E6EAF3', ink='#66748E'):
    canvas.delete('all')
    w=max(450,canvas.winfo_width()); h=max(190,canvas.winfo_height())
    left,right,top,bottom=48,20,24,39
    pw=max(1,w-left-right);ph=max(1,h-top-bottom)
    values=[max(0,float(v or 0)) for v in values]
    high=max(values,default=0); high=max(1,high*1.15)
    for i in range(5):
        y=top+ph*i/4
        canvas.create_line(left,y,w-right,y,fill=grid,dash=(3,5))
        canvas.create_text(left-9,y,text=f'{high*(4-i)/4:.0f}',anchor='e',fill=ink,font=('Segoe UI',9))
    if not values:
        canvas.create_text(w/2,h/2,text='Chưa có dữ liệu trong kỳ',fill=ink,font=('Segoe UI',11))
        return
    count=len(values); step=pw/max(1,count-1)
    coords=[(left+i*step,top+ph*(1-v/high)) for i,v in enumerate(values)]
    if len(coords)>1:
        flat=[n for point in coords for n in point]
        canvas.create_line(*flat,fill=line,width=3,smooth=False,capstyle='round',joinstyle='round')
    for i,(x,y) in enumerate(coords):
        canvas.create_oval(x-4,y-4,x+4,y+4,fill=dot,outline='white',width=1.5)
        if count<=10 or i%max(1,count//8)==0 or i==count-1:
            canvas.create_text(x,h-19,text=str(labels[i]) if i<len(labels) else str(i+1),fill=ink,font=('Segoe UI',9))
        if values[i] and count<=10:
            canvas.create_text(x,max(12,y-15),text=f'{values[i]:.0f}',fill=ink,font=('Segoe UI',9,'bold'))
