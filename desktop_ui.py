"""ChessLens desktop layout; game state remains in ScreenChess."""
import tkinter as tk
from tkinter import ttk

BG = '#101b1a'
CARD = '#192724'
TEXT = '#edf2e8'
MUTED = '#a3b5ab'
ACCENT = '#c8df89'


def build_ui(app):
    root = app.root
    root.title('ChessLens · Analysis studio')
    root.geometry(f'{min(1160, root.winfo_screenwidth()-60)}x{min(840, root.winfo_screenheight()-80)}')
    root.minsize(880, 620)
    root.configure(bg=BG)
    style=ttk.Style(root)
    style.theme_use('clam')
    style.configure('.', font=('Segoe UI', 10), background=BG, foreground=TEXT)
    style.configure('TFrame', background=BG)
    style.configure('Card.TFrame', background=CARD)
    style.configure('TLabel', background=BG, foreground=TEXT)
    style.configure('Card.TLabel', background=CARD)
    style.configure('Muted.TLabel', foreground=MUTED)
    style.configure('CardMuted.TLabel', background=CARD, foreground=MUTED)
    style.configure('Title.TLabel', font=('Segoe UI',26,'bold'))
    style.configure('Best.TLabel', background=CARD, foreground=ACCENT, font=('Segoe UI',44,'bold'))
    style.configure('Section.TLabel', font=('Segoe UI',11,'bold'), foreground=ACCENT)
    style.configure('TButton', padding=(14,10), background='#2b4039', foreground=TEXT, borderwidth=0)
    style.map('TButton', background=[('active','#395348'),('disabled','#24322d')],foreground=[('disabled','#73877b')])
    style.configure('Accent.TButton', background=ACCENT,foreground='#17291d',font=('Segoe UI',10,'bold'))
    style.map('Accent.TButton',background=[('active','#d9eda9'),('disabled','#475941')])
    style.configure('Stop.TButton',background='#5d3036',foreground='#ffe3e3')
    style.map('Stop.TButton',background=[('active','#82414a')])
    style.configure('TEntry',fieldbackground='#243830',foreground=TEXT,padding=8)
    style.configure('TCombobox',fieldbackground='#243830',foreground=TEXT,padding=7)
    style.map('TCombobox',fieldbackground=[('readonly','#243830')],foreground=[('readonly',TEXT)])
    style.configure('TCheckbutton', background=BG,foreground=TEXT,padding=8)
    style.map('TCheckbutton',background=[('active',BG)])
    style.configure('TNotebook', background=BG,borderwidth=0)
    style.configure('TNotebook.Tab',padding=(20,10),background=BG,foreground=MUTED)
    style.map('TNotebook.Tab',background=[('selected',CARD)],foreground=[('selected',ACCENT)])
    style.configure('Horizontal.TProgressbar',background=ACCENT,troughcolor=BG,borderwidth=0)

    header=ttk.Frame(root,padding=(24,18,24,12));header.pack(fill='x')
    ttk.Label(header,text='♞  ChessLens',style='Title.TLabel').pack(side='left')
    ttk.Label(header,text='A clearer view of your next move.',style='Muted.TLabel').pack(side='left',padx=22)
    app.stop_button=ttk.Button(header,text='Stop · Esc',style='Stop.TButton',command=app.stop);app.stop_button.pack(side='right')
    # The footer is outside the scroll area so progress and Stop stay reachable.
    footer=ttk.Frame(root,padding=(24,10));footer.pack(side='bottom',fill='x')
    app.progress=ttk.Progressbar(footer,mode='indeterminate');app.progress.pack(fill='x',pady=(0,8))
    app.status_label=ttk.Label(footer,textvariable=app.status,wraplength=1020);app.status_label.pack(anchor='w')
    footer.bind('<Configure>',lambda e:app.status_label.configure(wraplength=max(300,e.width-50)))
    ttk.Label(footer,textvariable=app.region_text,style='Muted.TLabel').pack(anchor='w',pady=(4,0))
    app.tabs=ttk.Notebook(root);app.tabs.pack(fill='both',expand=True,padx=24)
    workspace=ttk.Frame(app.tabs);settings_tab=ttk.Frame(app.tabs,padding=24);practice=ttk.Frame(app.tabs,padding=24)
    app.tabs.add(workspace,text='Analysis');app.tabs.add(settings_tab,text='Settings');app.tabs.add(practice,text='Practice')

    viewport=tk.Canvas(workspace,bg=BG,highlightthickness=0)
    scroll=ttk.Scrollbar(workspace,orient='vertical',command=viewport.yview);scroll.pack(side='right',fill='y')
    viewport.pack(fill='both',expand=True);viewport.configure(yscrollcommand=scroll.set)
    page=ttk.Frame(viewport,padding=(0,18,12,12));window=viewport.create_window(0,0,window=page,anchor='nw')
    page.bind('<Configure>',lambda e:viewport.configure(scrollregion=viewport.bbox('all')))
    viewport.bind('<Configure>',lambda e:viewport.itemconfigure(window,width=e.width))
    def wheel(event):
        if app.tabs.index(app.tabs.select())==0 and event.widget is not app.output:
            viewport.yview_scroll(-int(event.delta/120),'units')
    root.bind('<MouseWheel>',wheel)
    toolbar=ttk.Frame(page);toolbar.pack(fill='x',pady=(0,14))
    for label,fn,st in [('01  Select board',app.select_region,'TButton'),('02  Capture',app.capture,'TButton'),('03  Confirm & analyse',app.analyse,'Accent.TButton')]:
        ttk.Button(toolbar,text=label,command=fn,style=st).pack(side='left',padx=(0,8))
    ttk.Checkbutton(toolbar,text='Track changes',variable=app.auto,command=app.toggle_auto).pack(side='right')
    quick=ttk.Frame(page);quick.pack(fill='x',pady=(0,14))
    for label,var in [('To move',app.turn),('Bottom',app.orientation)]:
        ttk.Label(quick,text=label,style='Muted.TLabel').pack(side='left',padx=(0,8))
        select=ttk.Combobox(quick,textvariable=var,values=['white','black'],state='readonly',width=8)
        select.pack(side='left',padx=(0,16));select.bind('<<ComboboxSelected>>',app.reset)
    ttk.Button(quick,text='Move rights & engine settings',command=lambda:app.tabs.select(settings_tab)).pack(side='right')
    playbar = ttk.Frame(page)
    playbar.pack(fill='x', pady=(0, 14))

    ttk.Checkbutton(
        playbar,
        text='Auto play',
        variable=app.autoplay,
        command=app.toggle_play,
    ).pack(side='left')

    ttk.Label(
        playbar,
        text='Play as',
        style='Muted.TLabel',
    ).pack(side='left', padx=(16, 8))

    play_color = ttk.Combobox(
        playbar,
        textvariable=app.bot_color,
        values=['white', 'black'],
        state='readonly',
        width=8,
    )
    play_color.pack(side='left')
    play_color.bind('<<ComboboxSelected>>', lambda e: app.stop())
    body=ttk.Frame(page);body.pack(fill='both',expand=True);body.columnconfigure(0,weight=0);body.columnconfigure(1,weight=1);body.rowconfigure(0,weight=1)
    board_card=ttk.Frame(body,style='Card.TFrame',padding=16);board_card.grid(row=0,column=0,sticky='nsew',padx=(0,16))
    ttk.Label(board_card,text='BOARD WORKSPACE',style='CardMuted.TLabel').pack(anchor='w',pady=(0,10))
    boards=ttk.Notebook(board_card);boards.pack()
    detected=ttk.Frame(boards,style='Card.TFrame');captured=ttk.Frame(boards,style='Card.TFrame')
    boards.add(detected,text='Detected position');boards.add(captured,text='Original capture')
    app.canvas=tk.Canvas(detected,width=400,height=400,highlightthickness=0,bg='#243830');app.canvas.pack(pady=8)
    app.canvas.create_text(200,154,text='♞',fill=ACCENT,font=('Segoe UI Symbol',58))
    app.canvas.create_text(200,229,text='Start with a board',fill=TEXT,font=('Segoe UI',18,'bold'))
    app.canvas.create_text(200,266,text='Select the 64 squares, then capture.',fill=MUTED,font=('Segoe UI',10))
    app.canvas.bind('<Button-1>',app.edit_square)
    app.image_label=ttk.Label(captured,style='Card.TLabel');app.image_label.pack(pady=8)
    app.placeholder=tk.PhotoImage(width=400,height=400);app.placeholder.put('#243830',to=(0,0,400,400));app.image_label.configure(image=app.placeholder)
    ttk.Label(board_card,text='Review all pieces. Click a detected square to correct it.',style='CardMuted.TLabel',wraplength=400).pack(anchor='w',pady=(10,0))
    analysis=ttk.Frame(body,style='Card.TFrame',padding=22);analysis.grid(row=0,column=1,sticky='nsew')
    ttk.Label(analysis,text='ENGINE TOP CHOICE',style='CardMuted.TLabel').pack(anchor='w')
    ttk.Label(analysis,textvariable=app.best_text,style='Best.TLabel').pack(anchor='w',pady=(5,0))
    ttk.Label(analysis,textvariable=app.eval_text,style='Card.TLabel',wraplength=290).pack(anchor='w',pady=(0,18))
    ttk.Separator(analysis).pack(fill='x',pady=(0,18))
    ttk.Label(analysis,text='CANDIDATE LINES',style='CardMuted.TLabel').pack(anchor='w')
    app.output=tk.Text(analysis,height=11,width=28,wrap='word',state='disabled',bg=CARD,fg=TEXT,font=('Segoe UI',11),relief='flat',padx=0,pady=12,insertbackground=TEXT)
    app.output.pack(fill='both',expand=True)
    app.set_output('Your analysis will appear here.\n\nCapture a board, review the pieces, then confirm to explore the strongest continuations.')
    ttk.Button(analysis,text='Explore interactive report ↗',command=app.open_report,style='Accent.TButton').pack(fill='x',pady=(16,0))
    ttk.Label(page,textvariable=app.history_text,style='Muted.TLabel').pack(anchor='w',pady=(12,0))

    ttk.Label(settings_tab,text='Position & engine',style='Title.TLabel').pack(anchor='w')
    ttk.Label(settings_tab,text='Set information that a screenshot cannot tell us.',style='Muted.TLabel').pack(anchor='w',pady=(5,22))
    fields=ttk.Frame(settings_tab);fields.pack(fill='x')
    for i,(label,var,values) in enumerate([('Side to move',app.turn,['white','black']),('Color at bottom',app.orientation,['white','black']),('Castling rights',app.castling,None),('En-passant target',app.ep,None),('Search time (seconds)',app.seconds,None)]):
        row,col=divmod(i,3);box=ttk.Frame(fields);box.grid(row=row,column=col,sticky='ew',padx=(0,20),pady=(0,18));fields.columnconfigure(col,weight=1)
        ttk.Label(box,text=label,style='Muted.TLabel').pack(anchor='w',pady=(0,6))
        entry=ttk.Combobox(box,textvariable=var,values=values,state='readonly',width=15) if values else ttk.Entry(box,textvariable=var,width=15)
        entry.pack(fill='x')
        if values:entry.bind('<<ComboboxSelected>>',app.reset)
        elif var is not app.seconds:entry.bind('<KeyRelease>',app.reset)
    ttk.Label(settings_tab,text='Castling: KQkq = all rights; - = none. En-passant: target square or -.',style='Muted.TLabel').pack(anchor='w',pady=(0,20))
    ttk.Label(settings_tab,text='STOCKFISH',style='Section.TLabel').pack(anchor='w')
    app.engine_status=tk.StringVar(value='')
    def refresh_engine_status(*_):app.engine_status.set('Engine found · '+app.engine_path.get().replace('\\','/').split('/')[-1] if app.engine_path.get() else 'Engine missing · place Stockfish inside the stockfish folder')
    app.engine_path.trace_add('write',refresh_engine_status);refresh_engine_status()
    ttk.Label(settings_tab,textvariable=app.engine_status,style='Muted.TLabel').pack(anchor='w',pady=8)
    erow=ttk.Frame(settings_tab);erow.pack(fill='x');engine_entry=ttk.Entry(erow,textvariable=app.engine_path);engine_entry.pack(side='left',fill='x',expand=True);engine_entry.bind('<KeyRelease>',app.reset)
    ttk.Button(erow,text='Detect',command=app.detect_engine).pack(side='left',padx=8);ttk.Button(erow,text='Browse…',command=app.browse).pack(side='left')
    ttk.Label(settings_tab,text='ChessLens checks its stockfish folder automatically. Browse is only needed for a custom location.',style='Muted.TLabel',wraplength=720).pack(anchor='w',pady=12)

    ttk.Label(practice,text='Practice controls',style='Title.TLabel').pack(anchor='w')
    ttk.Label(practice,text='For local practice boards and games that permit engine assistance.',style='Muted.TLabel').pack(anchor='w',pady=(8,24))
    ttk.Checkbutton(practice,text='My board automatically promotes to queen',variable=app.autoqueen).pack(anchor='w',pady=(18,8))
    ttk.Label(practice,text='Confirm the position in Analysis first. Keep the external board visible and stationary. Hold Escape at any time to stop.',style='Muted.TLabel',wraplength=680).pack(anchor='w',pady=12)
