package pl.godziny.praca;

import android.app.Activity;
import android.app.AlertDialog;
import android.app.DatePickerDialog;
import android.app.TimePickerDialog;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.graphics.Typeface;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.HorizontalScrollView;
import android.widget.LinearLayout;
import android.widget.RadioGroup;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.List;
import java.util.Locale;
import java.util.TimeZone;

/**
 * Jedyny ekran: Clock In / Clock Out z licznikiem, podsumowanie wybranego tygodnia
 * (godziny i wypłata), lista wpisów z edycją oraz raport tygodnia do udostępnienia.
 */
public class MainActivity extends Activity {

    private static final String K_WEEK = "week_start";
    private static final long FORGOTTEN_AFTER = 12 * WorkMath.HOUR;
    private static final int REQ_EXPORT = 1, REQ_IMPORT = 2;

    /** Długości przerwy do wyboru w edycji (min). */
    static final int[] BREAKS = {0, 15, 30, 45, 60};

    private EntryStore store;
    private TimeZone tz;
    private long weekStart;

    private TextView status, timer, earned, earnedLabel, weekLabel, thisWeek;
    private TextView weekHours, weekHoursDec, weekPay, weekDays, emptyMsg;
    private Button rateBtn, clockBtn, nextWeek;
    private LinearLayout entryList;

    private final Handler handler = new Handler(Looper.getMainLooper());
    private long lastTickMinute = -1;
    private final Runnable ticker = new Runnable() {
        @Override public void run() {
            tick();
            handler.postDelayed(this, 1000 - System.currentTimeMillis() % 1000);
        }
    };

    @Override
    protected void attachBaseContext(Context base) {
        // Motyw wybrany w aplikacji (jak w telefonie / jasny / ciemny), patrz ThemePrefs.
        super.attachBaseContext(ThemePrefs.wrap(base));
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        store = new EntryStore(this);
        tz = TimeZone.getDefault();
        weekStart = currentWeekStart();
        if (savedInstanceState != null) {
            weekStart = savedInstanceState.getLong(K_WEEK, weekStart);   // np. po zmianie motywu
        }

        // Android 15+ rysuje pod paskami systemu: odsuń treść o ich wysokość.
        View root = findViewById(R.id.root);
        root.setOnApplyWindowInsetsListener((v, insets) -> {
            v.setPadding(insets.getSystemWindowInsetLeft(), insets.getSystemWindowInsetTop(),
                    insets.getSystemWindowInsetRight(), insets.getSystemWindowInsetBottom());
            return insets.consumeSystemWindowInsets();
        });

        status = findViewById(R.id.status);
        timer = findViewById(R.id.timer);
        earned = findViewById(R.id.earned);
        earnedLabel = findViewById(R.id.earnedLabel);
        weekLabel = findViewById(R.id.weekLabel);
        thisWeek = findViewById(R.id.thisWeek);
        weekHours = findViewById(R.id.weekHours);
        weekHoursDec = findViewById(R.id.weekHoursDec);
        weekPay = findViewById(R.id.weekPay);
        weekDays = findViewById(R.id.weekDays);
        emptyMsg = findViewById(R.id.emptyMsg);
        rateBtn = findViewById(R.id.rateBtn);
        clockBtn = findViewById(R.id.clockBtn);
        nextWeek = findViewById(R.id.nextWeek);
        entryList = findViewById(R.id.entryList);

        clockBtn.setOnClickListener(v -> toggleClock());
        rateBtn.setOnClickListener(v -> showSettings());
        findViewById(R.id.prevWeek).setOnClickListener(v -> moveWeek(-1));
        nextWeek.setOnClickListener(v -> moveWeek(1));
        thisWeek.setOnClickListener(v -> { weekStart = currentWeekStart(); refresh(); });
        findViewById(R.id.addEntry).setOnClickListener(v -> showEntryDialog(null));
        findViewById(R.id.reportBtn).setOnClickListener(v -> showReport());
        findViewById(R.id.undoBtn).setOnClickListener(v -> undoDelete());
    }

    @Override protected void onSaveInstanceState(Bundle out) {
        super.onSaveInstanceState(out);
        out.putLong(K_WEEK, weekStart);
    }

    @Override protected void onResume() {
        super.onResume();
        tz = TimeZone.getDefault();
        refresh();
        handler.post(ticker);
    }

    @Override protected void onPause() {
        super.onPause();
        handler.removeCallbacks(ticker);
    }

    private long currentWeekStart() {
        return WorkMath.weekStart(System.currentTimeMillis(), store.firstDay(), tz);
    }

    private void moveWeek(int delta) {
        long target = WorkMath.addWeeks(weekStart, delta, tz);
        if (target > currentWeekStart()) return;
        weekStart = target;
        refresh();
    }

    // ------------------------------------------------------------ odświeżanie

    private void tick() {
        long now = System.currentTimeMillis();
        Entry run = WorkMath.running(store.all());
        if (run == null) return;
        timer.setText(WorkMath.formatHms(now - run.start));
        long min = WorkMath.minutes(run, now);
        earned.setText(WorkMath.formatMoney(WorkMath.payCents(min, run.rateCents)));
        // Co pełną minutę przelicz tydzień i listę (godziny trwającej zmiany rosną).
        if (min != lastTickMinute) {
            lastTickMinute = min;
            refresh();
        }
    }

    void refresh() {
        long now = System.currentTimeMillis();
        long rate = store.rateCents();
        List<Entry> all = store.all();
        Entry run = WorkMath.running(all);

        rateBtn.setText(WorkMath.formatMoney(rate) + "/h  ✎");

        if (run != null) {
            status.setText("W pracy od " + fmt("HH:mm").format(run.start)
                    + (WorkMath.dayStart(run.start, tz) == WorkMath.dayStart(now, tz)
                    ? "" : " (" + Report.dayShort(run.start, tz) + " " + fmt("dd.MM").format(run.start) + ")"));
            status.setTextColor(getColor(R.color.green));
            if (now - run.start > FORGOTTEN_AFTER) {
                // Zapomniany Clock Out zawyża godziny: ostrzeż, zamiast liczyć po cichu.
                status.setText("Ponad 12 h od Clock In (" + fmt("HH:mm").format(run.start)
                        + "). Zapomniany Clock Out? Dotknij wpis, aby ustawić koniec.");
                status.setTextColor(getColor(R.color.red));
            }
            timer.setText(WorkMath.formatHms(now - run.start));
            timer.setTextColor(getColor(R.color.ink));
            long min = WorkMath.minutes(run, now);
            earned.setText(WorkMath.formatMoney(WorkMath.payCents(min, run.rateCents)));
            earned.setVisibility(View.VISIBLE);
            earnedLabel.setVisibility(View.VISIBLE);
            clockBtn.setText(R.string.clock_out);
            clockBtn.setBackgroundResource(R.drawable.btn_out);
        } else {
            status.setText(R.string.status_off);
            status.setTextColor(getColor(R.color.ink_dim));
            timer.setText("00:00:00");
            timer.setTextColor(getColor(R.color.line));
            earned.setVisibility(View.GONE);
            earnedLabel.setVisibility(View.GONE);
            clockBtn.setText(R.string.clock_in);
            clockBtn.setBackgroundResource(R.drawable.btn_in);
        }

        boolean current = weekStart == currentWeekStart();
        weekLabel.setText(Report.weekLabel(weekStart, tz));
        thisWeek.setVisibility(current ? View.GONE : View.VISIBLE);
        nextWeek.setEnabled(!current);
        nextWeek.setAlpha(current ? 0.35f : 1f);

        List<Entry> week = WorkMath.inRange(all, weekStart, WorkMath.addWeeks(weekStart, 1, tz));
        WorkMath.Summary s = WorkMath.summarize(week, now, tz);
        weekHours.setText(WorkMath.formatHm(s.minutes) + " h");
        weekHoursDec.setText("= " + WorkMath.formatDecimalHours(s.minutes) + " h");
        weekPay.setText(WorkMath.formatMoney(s.payCents));
        weekDays.setText("brutto · dni pracy: " + s.days);

        buildList(week, now);
    }

    private void buildList(List<Entry> week, long now) {
        entryList.removeAllViews();
        emptyMsg.setVisibility(week.isEmpty() ? View.VISIBLE : View.GONE);
        findViewById(R.id.editHint).setVisibility(week.isEmpty() ? View.GONE : View.VISIBLE);
        SimpleDateFormat hm = fmt("HH:mm");
        SimpleDateFormat dm = fmt("dd.MM");

        long day = -1;
        for (int i = 0; i < week.size(); i++) {
            Entry e = week.get(i);
            long d = WorkMath.dayStart(e.start, tz);
            if (d != day) {
                day = d;
                // Suma dnia (wpisy, które zaczęły się tego dnia).
                long dayMin = 0, dayPay = 0;
                for (Entry o : week) {
                    if (WorkMath.dayStart(o.start, tz) != d) continue;
                    long m = WorkMath.minutes(o, now);
                    dayMin += m;
                    dayPay += WorkMath.payCents(m, o.rateCents);
                }
                entryList.addView(dayHeader(d, Report.dayShort(e.start, tz) + " " + dm.format(e.start),
                        WorkMath.formatHm(dayMin) + " h · " + WorkMath.formatMoney(dayPay)));
            }
            long min = WorkMath.minutes(e, now);
            String range = hm.format(e.start) + " – " + (e.isRunning() ? "teraz" : hm.format(e.end));
            if (!e.isRunning() && WorkMath.dayStart(e.end, tz) != d) range += " (+1)";
            entryList.addView(entryRow(e, range, Report.notes(e, tz), WorkMath.formatHm(min) + " h",
                    WorkMath.formatMoney(WorkMath.payCents(min, e.rateCents))));
        }
    }

    private View dayHeader(long day, String left, String right) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);
        row.setMinimumHeight(dp(44));
        row.setPadding(dp(8), dp(10), dp(8), dp(2));
        row.setBackgroundResource(R.drawable.row_bg);
        row.setOnClickListener(v -> showDayDialog(day));
        row.setContentDescription("Dzień " + left + ": usuń albo dodaj wpis");
        TextView l = text(left + "  ⋯", 13, R.color.ink);
        l.setTypeface(Typeface.DEFAULT_BOLD);
        row.addView(l, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        TextView r = text(right, 13, R.color.ink_dim);
        r.setFontFeatureSettings("tnum");
        row.addView(r);
        return row;
    }

    private View entryRow(Entry e, String range, String notes, String dur, String pay) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);
        row.setMinimumHeight(dp(48));
        row.setPadding(dp(8), dp(6), dp(8), dp(6));
        row.setBackgroundResource(R.drawable.row_bg);
        row.setOnClickListener(v -> showEntryDialog(e));
        row.setContentDescription("Edytuj wpis " + range);

        LinearLayout left = new LinearLayout(this);
        left.setOrientation(LinearLayout.VERTICAL);
        TextView t = text(range, 16, e.isRunning() ? R.color.green : R.color.ink);
        t.setFontFeatureSettings("tnum");
        left.addView(t);
        if (!notes.isEmpty()) {
            // Przerwa i ślad poprawek widoczne od razu na liście, nie tylko w raporcie.
            TextView nt = text((e.isEdited() ? "✎ " : "") + notes, 12, R.color.ink_dim);
            left.addView(nt);
        }
        row.addView(left, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));

        TextView dv = text(dur, 15, R.color.ink_dim);
        dv.setFontFeatureSettings("tnum");
        dv.setGravity(Gravity.END);
        row.addView(dv, new LinearLayout.LayoutParams(dp(64), ViewGroup.LayoutParams.WRAP_CONTENT));

        TextView pv = text(pay, 15, R.color.green);
        pv.setFontFeatureSettings("tnum");
        pv.setTypeface(Typeface.create("sans-serif-medium", Typeface.NORMAL));
        pv.setGravity(Gravity.END);
        row.addView(pv, new LinearLayout.LayoutParams(dp(92), ViewGroup.LayoutParams.WRAP_CONTENT));
        return row;
    }

    // ------------------------------------------------------------ Clock In / Clock Out

    private void toggleClock() {
        long now = System.currentTimeMillis();
        List<Entry> all = store.all();
        Entry run = WorkMath.running(all);
        if (run != null) {
            long min = (now - run.start) / WorkMath.MINUTE;
            if (min < 1) {
                store.delete(run.id);
                toast("Zmiana krótsza niż minuta — nie zapisano.");
            } else {
                Entry done = run.clockedOut(now);
                store.update(done);
                long paid = WorkMath.minutes(done, now);
                toast("Zapisano: " + WorkMath.formatHm(paid) + " h · "
                        + WorkMath.formatMoney(WorkMath.payCents(paid, done.rateCents)));
            }
        } else {
            String err = WorkMath.validate(all, -1, now, 0, now, tz);
            if (err != null) {
                toast(err);
                return;
            }
            store.add(now, 0);
            weekStart = currentWeekStart();
        }
        lastTickMinute = -1;
        refresh();
    }

    // ------------------------------------------------------------ edycja wpisu

    /** Dialog dodawania (entry == null) albo edycji wpisu. */
    private void showEntryDialog(Entry entry) {
        showEntryDialog(entry, -1);
    }

    /** {@code presetDay}: początek dnia dla nowego wpisu (-1 = dziś albo początek tygodnia). */
    private void showEntryDialog(Entry entry, long presetDay) {
        long now = System.currentTimeMillis();
        final long[] start = new long[1];
        final long[] end = new long[1];
        if (entry != null) {
            start[0] = entry.start;
            end[0] = entry.end;
        } else {
            long weekEnd = WorkMath.addWeeks(weekStart, 1, tz);
            long day = presetDay >= 0 ? presetDay
                    : (now >= weekStart && now < weekEnd) ? WorkMath.dayStart(now, tz) : weekStart;
            start[0] = WorkMath.atTime(day, 8, 0, tz);    // domyślnie 08:00–16:00
            end[0] = WorkMath.atTime(day, 16, 0, tz);
            if (end[0] > now) {                            // dziś przed 16:00: kończ „teraz”
                end[0] = now - now % WorkMath.MINUTE;
                start[0] = Math.max(WorkMath.dayStart(now, tz), end[0] - 8 * WorkMath.HOUR);
            }
        }
        // Trwająca zmiana: koniec = „teraz”, dopóki nie ustawisz końca (to ją zakończy).
        final boolean[] running = {entry != null && entry.isRunning()};
        final int[] brk = {entry != null ? entry.breakMin : 0};
        final long rate = entry != null ? entry.rateCents : store.rateCents();

        View v = getLayoutInflater().inflate(R.layout.dialog_entry, null);
        Button dateBtn = v.findViewById(R.id.dateBtn);
        Button startBtn = v.findViewById(R.id.startBtn);
        Button endBtn = v.findViewById(R.id.endBtn);
        TextView summary = v.findViewById(R.id.summary);
        TextView hint = v.findViewById(R.id.hint);
        TextView error = v.findViewById(R.id.error);
        TextView clockInfo = v.findViewById(R.id.clockInfo);
        Button[] breakBtns = new Button[BREAKS.length];
        int[] breakIds = {R.id.break0, R.id.break15, R.id.break30, R.id.break45, R.id.break60};
        for (int i = 0; i < BREAKS.length; i++) breakBtns[i] = v.findViewById(breakIds[i]);
        if (entry != null && !entry.manual) {
            clockInfo.setText("Z zegara: " + fmt("HH:mm").format(entry.origStart) + " – "
                    + (entry.origEnd == 0 ? (entry.isRunning() ? "trwa" : "brak Clock Out")
                    : fmt("HH:mm").format(entry.origEnd)) + "  (zachowane w raporcie)");
            clockInfo.setVisibility(View.VISIBLE);
        }

        Runnable update = () -> {
            long n = System.currentTimeMillis();
            Calendar c = cal(start[0]);
            dateBtn.setText(Report.dayShort(start[0], tz) + " " + fmt("dd.MM.yyyy").format(start[0]));
            startBtn.setText(fmt("HH:mm").format(c.getTime()));
            endBtn.setText(running[0] ? "trwa… ✎" : fmt("HH:mm").format(end[0]));
            Entry probe = new Entry(-1, start[0], running[0] ? 0 : end[0], brk[0], rate, 0, 0, true);
            long min = WorkMath.minutes(probe, n);
            summary.setText(WorkMath.formatHm(min) + " h  ·  " + WorkMath.formatMoney(WorkMath.payCents(min, rate))
                    + "   (" + WorkMath.formatMoney(rate) + "/h)");
            for (int i = 0; i < BREAKS.length; i++) breakBtns[i].setSelected(brk[0] == BREAKS[i]);
            if (!running[0] && WorkMath.dayStart(end[0], tz) != WorkMath.dayStart(start[0], tz)) {
                hint.setText("Koniec następnego dnia: " + Report.dayShort(end[0], tz) + " "
                        + fmt("dd.MM").format(end[0]) + " (zmiana przez północ)");
                hint.setVisibility(View.VISIBLE);
            } else if (running[0]) {
                hint.setText("Zmiana trwa. Odejmowanie czasu przesuwa początek. "
                        + "Ustaw koniec, aby zakończyć zmianę.");
                hint.setVisibility(View.VISIBLE);
            } else {
                hint.setVisibility(View.GONE);
            }
            error.setVisibility(View.GONE);
        };
        update.run();

        dateBtn.setOnClickListener(b -> {
            Calendar c = cal(start[0]);
            DatePickerDialog dp = new DatePickerDialog(this, (picker, y, m, d) -> {
                Calendar s = cal(start[0]);
                Calendar oldEnd = cal(end[0]);
                s.set(y, m, d);
                start[0] = s.getTimeInMillis();
                if (!running[0]) end[0] = WorkMath.endAfter(start[0], oldEnd.get(Calendar.HOUR_OF_DAY),
                        oldEnd.get(Calendar.MINUTE), oldEnd.get(Calendar.SECOND), tz);
                update.run();
            }, c.get(Calendar.YEAR), c.get(Calendar.MONTH), c.get(Calendar.DAY_OF_MONTH));
            dp.getDatePicker().setMaxDate(System.currentTimeMillis());
            dp.getDatePicker().setFirstDayOfWeek(store.firstDay());
            dp.show();
        });

        startBtn.setOnClickListener(b -> {
            Calendar c = cal(start[0]);
            new TimePickerDialog(this, (picker, h, m) -> {
                Calendar s = cal(start[0]);
                Calendar oldEnd = cal(end[0]);
                s.set(Calendar.HOUR_OF_DAY, h);
                s.set(Calendar.MINUTE, m);
                s.set(Calendar.SECOND, 0);
                s.set(Calendar.MILLISECOND, 0);
                start[0] = s.getTimeInMillis();
                if (!running[0]) end[0] = WorkMath.endAfter(start[0], oldEnd.get(Calendar.HOUR_OF_DAY),
                        oldEnd.get(Calendar.MINUTE), oldEnd.get(Calendar.SECOND), tz);
                update.run();
            }, c.get(Calendar.HOUR_OF_DAY), c.get(Calendar.MINUTE), true).show();
        });

        endBtn.setOnClickListener(b -> {
            Calendar c = cal(running[0] ? System.currentTimeMillis() : end[0]);
            new TimePickerDialog(this, (picker, h, m) -> {
                end[0] = WorkMath.endAfter(start[0], h, m, 0, tz);
                running[0] = false;
                update.run();
            }, c.get(Calendar.HOUR_OF_DAY), c.get(Calendar.MINUTE), true).show();
        });

        for (int i = 0; i < BREAKS.length; i++) {
            int minutes = BREAKS[i];
            breakBtns[i].setOnClickListener(b -> {
                brk[0] = minutes;
                update.run();
            });
        }

        long[] deltas = {-WorkMath.HOUR, -15 * WorkMath.MINUTE, 15 * WorkMath.MINUTE, WorkMath.HOUR};
        int[] ids = {R.id.minus60, R.id.minus15, R.id.plus15, R.id.plus60};
        for (int i = 0; i < ids.length; i++) {
            long delta = deltas[i];
            v.findViewById(ids[i]).setOnClickListener(b -> {
                long[] r = WorkMath.adjust(start[0], running[0] ? 0 : end[0], delta,
                        System.currentTimeMillis());
                if (r == null) {
                    error.setText(delta < 0 ? "Nie można odjąć więcej, niż trwa wpis."
                            : "Koniec nie może być w przyszłości.");
                    error.setVisibility(View.VISIBLE);
                    return;
                }
                start[0] = r[0];
                if (!running[0]) end[0] = r[1];
                update.run();
            });
        }

        AlertDialog.Builder b = new AlertDialog.Builder(this)
                .setTitle(entry == null ? "Nowy wpis" : "Edytuj wpis")
                .setView(v)
                .setPositiveButton("Zapisz", null)
                .setNegativeButton("Anuluj", null);
        if (entry != null) b.setNeutralButton("Usuń", null);
        AlertDialog dlg = b.create();
        dlg.setOnShowListener(d -> {
            dlg.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(x -> {
                long n = System.currentTimeMillis();
                long e = running[0] ? 0 : end[0];
                String err = WorkMath.validate(store.all(), entry == null ? -1 : entry.id,
                        start[0], e, brk[0], n, tz);
                if (err != null) {
                    error.setText(err);
                    error.setVisibility(View.VISIBLE);
                    return;
                }
                if (entry == null) store.addManual(start[0], e, brk[0]);
                else store.update(entry.withTimes(start[0], e).withBreak(brk[0]));
                lastTickMinute = -1;
                weekStart = WorkMath.weekStart(start[0], store.firstDay(), tz);
                dlg.dismiss();
                refresh();
            });
            if (entry != null) {
                dlg.getButton(AlertDialog.BUTTON_NEUTRAL).setTextColor(getColor(R.color.red));
                dlg.getButton(AlertDialog.BUTTON_NEUTRAL).setOnClickListener(x ->
                        new AlertDialog.Builder(this)
                                .setMessage("Usunąć wpis " + Report.dayShort(entry.start, tz) + " "
                                        + fmt("dd.MM HH:mm").format(entry.start) + "?")
                                .setPositiveButton("Usuń", (dd, w) -> {
                                    dlg.dismiss();
                                    deleteWithUndo(java.util.Collections.singletonList(entry),
                                            "Usunięto wpis " + Report.dayShort(entry.start, tz) + " "
                                                    + fmt("dd.MM HH:mm").format(entry.start));
                                })
                                .setNegativeButton("Anuluj", null)
                                .show());
            }
        });
        dlg.show();
    }

    // ------------------------------------------------------------ cały dzień i „Cofnij”

    /** Okno dnia: lista wpisów z sumą, usunięcie całego dnia albo dodanie wpisu w tym dniu. */
    private void showDayDialog(long day) {
        long now = System.currentTimeMillis();
        List<Entry> entries = WorkMath.inRange(store.all(), day, WorkMath.addDays(day, 1, tz));
        if (entries.isEmpty()) return;
        long min = 0, pay = 0;
        StringBuilder sb = new StringBuilder();
        SimpleDateFormat hm = fmt("HH:mm");
        for (Entry e : entries) {
            long m = WorkMath.minutes(e, now);
            min += m;
            pay += WorkMath.payCents(m, e.rateCents);
            sb.append("• ").append(hm.format(e.start)).append(" – ")
                    .append(e.isRunning() ? "teraz (trwa)" : hm.format(e.end))
                    .append("   ").append(WorkMath.formatHm(m)).append(" h\n");
        }
        sb.append("\nRazem: ").append(WorkMath.formatHm(min)).append(" h · ")
                .append(WorkMath.formatMoney(pay));
        String label = Report.dayShort(day, tz) + " " + fmt("dd.MM.yyyy").format(day);
        AlertDialog dlg = new AlertDialog.Builder(this)
                .setTitle(label)
                .setMessage(sb.toString())
                .setPositiveButton("Usuń dzień", (d, w) -> deleteWithUndo(entries,
                        "Usunięto " + Report.dayShort(day, tz) + " " + fmt("dd.MM").format(day) + ": "
                                + WorkMath.formatHm(WorkMath.summarize(entries, now, tz).minutes) + " h"))
                .setNeutralButton("Dodaj", (d, w) -> {
                    if (day <= now) showEntryDialog(null, day);
                })
                .setNegativeButton("Anuluj", null)
                .create();
        dlg.setOnShowListener(d -> dlg.getButton(AlertDialog.BUTTON_POSITIVE)
                .setTextColor(getColor(R.color.red)));
        dlg.show();
    }

    private List<Entry> lastDeleted;
    private final Runnable hideUndo = () -> {
        lastDeleted = null;
        findViewById(R.id.undoBar).setVisibility(View.GONE);
    };

    /** Usuwa wpisy i przez 15 s pokazuje „Cofnij”, które je przywraca 1:1. */
    private void deleteWithUndo(List<Entry> entries, String message) {
        java.util.List<Long> ids = new java.util.ArrayList<>();
        for (Entry e : entries) ids.add(e.id);
        store.deleteAll(ids);
        lastDeleted = new java.util.ArrayList<>(entries);
        ((TextView) findViewById(R.id.undoText)).setText(message);
        findViewById(R.id.undoBar).setVisibility(View.VISIBLE);
        handler.removeCallbacks(hideUndo);
        handler.postDelayed(hideUndo, 15_000);
        lastTickMinute = -1;
        refresh();
    }

    private void undoDelete() {
        if (lastDeleted != null) {
            int n = store.restore(lastDeleted);
            toast(n == lastDeleted.size() ? "Przywrócono (" + n + ")."
                    : "Przywrócono " + n + " z " + lastDeleted.size()
                    + " — trwającej zmiany nie, bo trwa już nowa.");
        }
        handler.removeCallbacks(hideUndo);
        hideUndo.run();
        lastTickMinute = -1;
        refresh();
    }

    // ------------------------------------------------------------ ustawienia

    /** Dni w kolejności listy (od poniedziałku) jako stałe Calendar.DAY_OF_WEEK. */
    static final int[] WEEK_DAYS = {Calendar.MONDAY, Calendar.TUESDAY, Calendar.WEDNESDAY,
            Calendar.THURSDAY, Calendar.FRIDAY, Calendar.SATURDAY, Calendar.SUNDAY};

    private void showSettings() {
        View v = getLayoutInflater().inflate(R.layout.dialog_settings, null);
        EditText input = v.findViewById(R.id.rateInput);
        CheckBox rateThisWeek = v.findViewById(R.id.rateThisWeek);
        Spinner weekDay = v.findViewById(R.id.weekStart);
        TextView err = v.findViewById(R.id.rateError);
        input.setText(WorkMath.rateForInput(store.rateCents()));
        input.setSelection(input.getText().length());

        String[] names = new String[WEEK_DAYS.length];
        int selected = 0;
        for (int i = 0; i < WEEK_DAYS.length; i++) {
            names[i] = Report.DAYS_FULL[WEEK_DAYS[i]] + ", 00:00";
            if (WEEK_DAYS[i] == store.firstDay()) selected = i;
        }
        ArrayAdapter<String> days = new ArrayAdapter<>(this, android.R.layout.simple_spinner_item, names);
        days.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        weekDay.setAdapter(days);
        weekDay.setSelection(selected);

        RadioGroup themeGroup = v.findViewById(R.id.themeMode);
        int theme = ThemePrefs.get(this);
        themeGroup.check(theme == ThemePrefs.MODE_DARK ? R.id.themeDark
                : theme == ThemePrefs.MODE_LIGHT ? R.id.themeLight : R.id.themeSystem);

        AlertDialog dlg = new AlertDialog.Builder(this)
                .setTitle("Ustawienia")
                .setView(v)
                .setPositiveButton("Zapisz", null)
                .setNegativeButton("Anuluj", null)
                .create();
        v.findViewById(R.id.exportBtn).setOnClickListener(x -> {
            dlg.dismiss();
            exportCsv();
        });
        v.findViewById(R.id.importBtn).setOnClickListener(x -> {
            dlg.dismiss();
            importCsv();
        });
        dlg.setOnShowListener(d -> dlg.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(x -> {
            long cents = WorkMath.parseRate(input.getText().toString());
            if (cents <= 0) {
                err.setText("Wpisz stawkę, np. 34 albo 34.50");
                err.setVisibility(View.VISIBLE);
                return;
            }
            if (cents != store.rateCents()) {
                // Historia zostaje przy starej stawce; bieżący tydzień — według wyboru.
                store.setRateCents(cents, rateThisWeek.isChecked() ? currentWeekStart() : Long.MAX_VALUE);
            }
            int first = WEEK_DAYS[weekDay.getSelectedItemPosition()];
            store.setFirstDay(first);
            weekStart = WorkMath.weekStart(weekStart, first, tz);
            int id = themeGroup.getCheckedRadioButtonId();
            int chosen = id == R.id.themeDark ? ThemePrefs.MODE_DARK
                    : id == R.id.themeLight ? ThemePrefs.MODE_LIGHT : ThemePrefs.MODE_SYSTEM;
            dlg.dismiss();
            if (chosen != ThemePrefs.get(this)) {
                ThemePrefs.set(this, chosen);
                recreate();   // nowy motyw wymaga ponownego utworzenia ekranu
                return;
            }
            refresh();
        }));
        dlg.show();
    }

    // ------------------------------------------------------------ kopia CSV

    private void exportCsv() {
        String name = "godziny-pracy-" + fmt("yyyy-MM-dd").format(System.currentTimeMillis()) + ".csv";
        Intent i = new Intent(Intent.ACTION_CREATE_DOCUMENT)
                .addCategory(Intent.CATEGORY_OPENABLE)
                .setType("text/csv")
                .putExtra(Intent.EXTRA_TITLE, name);
        startActivityForResult(i, REQ_EXPORT);
    }

    private void importCsv() {
        Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT)
                .addCategory(Intent.CATEGORY_OPENABLE)
                .setType("*/*")
                .putExtra(Intent.EXTRA_MIME_TYPES, new String[]{"text/csv",
                        "text/comma-separated-values", "text/plain", "application/octet-stream"});
        startActivityForResult(i, REQ_IMPORT);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (resultCode != RESULT_OK || data == null || data.getData() == null) return;
        Uri uri = data.getData();
        if (requestCode == REQ_EXPORT) {
            // BOM, żeby Excel rozpoznał UTF-8 (polskie znaki w kolumnie dnia).
            String csv = "\uFEFF" + Csv.export(store.all(), System.currentTimeMillis(), tz);
            try (OutputStream out = getContentResolver().openOutputStream(uri, "wt")) {
                if (out == null) throw new IOException("brak pliku");
                out.write(csv.getBytes(StandardCharsets.UTF_8));
                toast("Zapisano kopię: " + store.all().size() + " wpisów.");
            } catch (IOException | RuntimeException e) {
                toast("Nie udało się zapisać pliku.");
            }
        } else if (requestCode == REQ_IMPORT) {
            String text;
            try (InputStream in = getContentResolver().openInputStream(uri)) {
                if (in == null) throw new IOException("brak pliku");
                ByteArrayOutputStream buf = new ByteArrayOutputStream();
                byte[] b = new byte[8192];
                int n;
                while ((n = in.read(b)) > 0) {
                    buf.write(b, 0, n);
                    if (buf.size() > 5_000_000) throw new IOException("za duży");
                }
                text = new String(buf.toByteArray(), StandardCharsets.UTF_8);
            } catch (IOException | RuntimeException e) {
                toast("Nie udało się odczytać pliku.");
                return;
            }
            Csv.Result r = Csv.parse(text);
            if (r.error != null) {
                new AlertDialog.Builder(this).setTitle("Nie przywrócono")
                        .setMessage(r.error).setPositiveButton("OK", null).show();
                return;
            }
            new AlertDialog.Builder(this)
                    .setTitle("Przywrócić kopię?")
                    .setMessage("Obecne wpisy (" + store.all().size() + ") zostaną zastąpione "
                            + r.entries.size() + " wpisami z pliku.")
                    .setPositiveButton("Przywróć", (d, w) -> {
                        store.replaceAll(r.entries);
                        lastTickMinute = -1;
                        refresh();
                        toast("Przywrócono " + r.entries.size() + " wpisów.");
                    })
                    .setNegativeButton("Anuluj", null)
                    .show();
        }
    }

    // ------------------------------------------------------------ raport

    private void showReport() {
        long now = System.currentTimeMillis();
        List<Entry> week = WorkMath.inRange(store.all(), weekStart, WorkMath.addWeeks(weekStart, 1, tz));
        String report = Report.build(week, weekStart, now, tz);

        TextView t = text(report, 12, R.color.ink);
        t.setTypeface(Typeface.MONOSPACE);
        t.setTextIsSelectable(true);
        t.setPadding(dp(20), dp(12), dp(20), dp(8));
        HorizontalScrollView h = new HorizontalScrollView(this);
        h.addView(t);
        ScrollView sv = new ScrollView(this);
        sv.addView(h);

        new AlertDialog.Builder(this)
                .setTitle("Raport tygodnia")
                .setView(sv)
                .setPositiveButton("Udostępnij", (d, w) -> {
                    Intent send = new Intent(Intent.ACTION_SEND)
                            .setType("text/plain")
                            .putExtra(Intent.EXTRA_SUBJECT, "Godziny pracy " + Report.weekLabel(weekStart, tz))
                            .putExtra(Intent.EXTRA_TEXT, report);
                    startActivity(Intent.createChooser(send, "Wyślij raport"));
                })
                .setNeutralButton("Kopiuj", (d, w) -> {
                    ClipboardManager cm = getSystemService(ClipboardManager.class);
                    cm.setPrimaryClip(ClipData.newPlainText("Raport godzin", report));
                    toast("Skopiowano raport.");
                })
                .setNegativeButton("Zamknij", null)
                .show();
    }

    // ------------------------------------------------------------ pomocnicze

    private Calendar cal(long t) {
        Calendar c = Calendar.getInstance(tz);
        c.setTimeInMillis(t);
        return c;
    }

    private SimpleDateFormat fmt(String pattern) {
        SimpleDateFormat f = new SimpleDateFormat(pattern, Locale.US);
        f.setTimeZone(tz);
        return f;
    }

    private TextView text(String s, int sp, int color) {
        TextView t = new TextView(this);
        t.setText(s);
        t.setTextSize(sp);
        t.setTextColor(getColor(color));
        return t;
    }

    private int dp(int v) {
        return Math.round(v * getResources().getDisplayMetrics().density);
    }

    private void toast(String s) {
        Toast.makeText(this, s, Toast.LENGTH_SHORT).show();
    }
}
