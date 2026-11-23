package pl.godziny.praca;

import android.app.Activity;
import android.app.AlertDialog;
import android.app.DatePickerDialog;
import android.app.TimePickerDialog;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Intent;
import android.graphics.Typeface;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.HorizontalScrollView;
import android.widget.LinearLayout;
import android.widget.RadioGroup;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

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
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        store = new EntryStore(this);
        tz = TimeZone.getDefault();
        weekStart = currentWeekStart();

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
        earned.setText(WorkMath.formatMoney(WorkMath.payCents(min, store.rateCents())));
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
            timer.setText(WorkMath.formatHms(now - run.start));
            timer.setTextColor(getColor(R.color.ink));
            long min = WorkMath.minutes(run, now);
            earned.setText(WorkMath.formatMoney(WorkMath.payCents(min, rate)));
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
        WorkMath.Summary s = WorkMath.summarize(week, rate, now, tz);
        weekHours.setText(WorkMath.formatHm(s.minutes) + " h");
        weekHoursDec.setText("= " + WorkMath.formatDecimalHours(s.minutes) + " h");
        weekPay.setText(WorkMath.formatMoney(s.payCents));
        weekDays.setText("dni pracy: " + s.days);

        buildList(week, rate, now);
    }

    private void buildList(List<Entry> week, long rate, long now) {
        entryList.removeAllViews();
        emptyMsg.setVisibility(week.isEmpty() ? View.VISIBLE : View.GONE);
        SimpleDateFormat hm = fmt("HH:mm");
        SimpleDateFormat dm = fmt("dd.MM");

        long day = -1;
        for (int i = 0; i < week.size(); i++) {
            Entry e = week.get(i);
            long d = WorkMath.dayStart(e.start, tz);
            if (d != day) {
                day = d;
                // Suma dnia (wpisy, które zaczęły się tego dnia).
                long dayMin = 0;
                for (Entry o : week) if (WorkMath.dayStart(o.start, tz) == d) dayMin += WorkMath.minutes(o, now);
                entryList.addView(dayHeader(Report.dayShort(e.start, tz) + " " + dm.format(e.start),
                        WorkMath.formatHm(dayMin) + " h · "
                                + WorkMath.formatMoney(WorkMath.payCents(dayMin, rate))));
            }
            long min = WorkMath.minutes(e, now);
            String range = hm.format(e.start) + " – " + (e.isRunning() ? "teraz" : hm.format(e.end));
            if (!e.isRunning() && WorkMath.dayStart(e.end, tz) != d) range += " (+1)";
            entryList.addView(entryRow(e, range, WorkMath.formatHm(min) + " h",
                    WorkMath.formatMoney(WorkMath.payCents(min, rate))));
        }
    }

    private View dayHeader(String left, String right) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setPadding(dp(8), dp(14), dp(8), dp(2));
        TextView l = text(left, 13, R.color.ink);
        l.setTypeface(Typeface.DEFAULT_BOLD);
        row.addView(l, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        TextView r = text(right, 13, R.color.ink_dim);
        r.setFontFeatureSettings("tnum");
        row.addView(r);
        return row;
    }

    private View entryRow(Entry e, String range, String dur, String pay) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);
        row.setMinimumHeight(dp(48));
        row.setPadding(dp(8), dp(6), dp(8), dp(6));
        row.setBackgroundResource(R.drawable.row_bg);
        row.setOnClickListener(v -> showEntryDialog(e));
        row.setContentDescription("Edytuj wpis " + range);

        TextView t = text(range, 16, e.isRunning() ? R.color.green : R.color.ink);
        t.setFontFeatureSettings("tnum");
        row.addView(t, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));

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
                store.update(run.withTimes(run.start, now));
                toast("Zapisano: " + WorkMath.formatHm(min) + " h · "
                        + WorkMath.formatMoney(WorkMath.payCents(min, store.rateCents())));
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
        long now = System.currentTimeMillis();
        final long[] start = new long[1];
        final long[] end = new long[1];
        if (entry != null) {
            start[0] = entry.start;
            end[0] = entry.end;
        } else {
            long weekEnd = WorkMath.addWeeks(weekStart, 1, tz);
            long day = (now >= weekStart && now < weekEnd) ? WorkMath.dayStart(now, tz) : weekStart;
            start[0] = WorkMath.atTime(day, 8, 0, tz);    // domyślnie 08:00–16:00
            end[0] = WorkMath.atTime(day, 16, 0, tz);
            if (end[0] > now) {                            // dziś przed 16:00: kończ „teraz”
                end[0] = now - now % WorkMath.MINUTE;
                start[0] = Math.max(WorkMath.dayStart(now, tz), end[0] - 8 * WorkMath.HOUR);
            }
        }
        final boolean running = entry != null && entry.isRunning();

        View v = getLayoutInflater().inflate(R.layout.dialog_entry, null);
        Button dateBtn = v.findViewById(R.id.dateBtn);
        Button startBtn = v.findViewById(R.id.startBtn);
        Button endBtn = v.findViewById(R.id.endBtn);
        TextView summary = v.findViewById(R.id.summary);
        TextView hint = v.findViewById(R.id.hint);
        TextView error = v.findViewById(R.id.error);

        Runnable update = () -> {
            long n = System.currentTimeMillis();
            Calendar c = cal(start[0]);
            dateBtn.setText(Report.dayShort(start[0], tz) + " " + fmt("dd.MM.yyyy").format(start[0]));
            startBtn.setText(fmt("HH:mm").format(c.getTime()));
            endBtn.setText(running ? "trwa…" : fmt("HH:mm").format(end[0]));
            Entry probe = new Entry(-1, start[0], end[0]);
            long min = WorkMath.minutes(probe, n);
            summary.setText(WorkMath.formatHm(min) + " h  ·  "
                    + WorkMath.formatMoney(WorkMath.payCents(min, store.rateCents())));
            if (!running && WorkMath.dayStart(end[0], tz) != WorkMath.dayStart(start[0], tz)) {
                hint.setText("Koniec następnego dnia: " + Report.dayShort(end[0], tz) + " "
                        + fmt("dd.MM").format(end[0]) + " (zmiana przez północ)");
                hint.setVisibility(View.VISIBLE);
            } else if (running) {
                hint.setText("Zmiana trwa. Koniec ustawi przycisk Clock Out.");
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
                if (!running) end[0] = WorkMath.endAfter(start[0], oldEnd.get(Calendar.HOUR_OF_DAY),
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
                if (!running) end[0] = WorkMath.endAfter(start[0], oldEnd.get(Calendar.HOUR_OF_DAY),
                        oldEnd.get(Calendar.MINUTE), oldEnd.get(Calendar.SECOND), tz);
                update.run();
            }, c.get(Calendar.HOUR_OF_DAY), c.get(Calendar.MINUTE), true).show();
        });

        endBtn.setEnabled(!running);
        endBtn.setOnClickListener(b -> {
            Calendar c = cal(end[0]);
            new TimePickerDialog(this, (picker, h, m) -> {
                end[0] = WorkMath.endAfter(start[0], h, m, 0, tz);
                update.run();
            }, c.get(Calendar.HOUR_OF_DAY), c.get(Calendar.MINUTE), true).show();
        });

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
                String err = WorkMath.validate(store.all(), entry == null ? -1 : entry.id,
                        start[0], end[0], n, tz);
                if (err != null) {
                    error.setText(err);
                    error.setVisibility(View.VISIBLE);
                    return;
                }
                if (entry == null) store.add(start[0], end[0]);
                else store.update(entry.withTimes(start[0], end[0]));
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
                                    store.delete(entry.id);
                                    dlg.dismiss();
                                    refresh();
                                })
                                .setNegativeButton("Anuluj", null)
                                .show());
            }
        });
        dlg.show();
    }

    // ------------------------------------------------------------ ustawienia

    private void showSettings() {
        View v = getLayoutInflater().inflate(R.layout.dialog_settings, null);
        EditText input = v.findViewById(R.id.rateInput);
        RadioGroup group = v.findViewById(R.id.weekStart);
        TextView err = v.findViewById(R.id.rateError);
        input.setText(WorkMath.rateForInput(store.rateCents()));
        input.setSelection(input.getText().length());
        group.check(store.firstDay() == Calendar.SUNDAY ? R.id.startSun : R.id.startMon);

        AlertDialog dlg = new AlertDialog.Builder(this)
                .setTitle("Ustawienia")
                .setView(v)
                .setPositiveButton("Zapisz", null)
                .setNegativeButton("Anuluj", null)
                .create();
        dlg.setOnShowListener(d -> dlg.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(x -> {
            long cents = WorkMath.parseRate(input.getText().toString());
            if (cents <= 0) {
                err.setText("Wpisz stawkę, np. 34 albo 34.50");
                err.setVisibility(View.VISIBLE);
                return;
            }
            store.setRateCents(cents);
            int first = group.getCheckedRadioButtonId() == R.id.startSun ? Calendar.SUNDAY : Calendar.MONDAY;
            store.setFirstDay(first);
            weekStart = WorkMath.weekStart(weekStart, first, tz);
            dlg.dismiss();
            refresh();
        }));
        dlg.show();
    }

    // ------------------------------------------------------------ raport

    private void showReport() {
        long now = System.currentTimeMillis();
        List<Entry> week = WorkMath.inRange(store.all(), weekStart, WorkMath.addWeeks(weekStart, 1, tz));
        String report = Report.build(week, weekStart, store.rateCents(), now, tz);

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
