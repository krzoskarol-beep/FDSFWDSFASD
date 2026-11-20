package pl.pozycja.polska;

import android.Manifest;
import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.res.ColorStateList;
import android.graphics.Typeface;
import android.location.Location;
import android.location.LocationListener;
import android.location.LocationManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import android.view.View;
import android.view.ViewGroup;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputMethodManager;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import java.util.ArrayList;
import java.util.List;

/** Jedyny ekran: stan, konfiguracja, wybór miejsca w Polsce i sprawdzenie pozycji. */
public class MainActivity extends Activity {

    private static final int REQ_NOTIF = 1;
    private static final int REQ_LOCATION = 2;
    private static final int COLUMNS = 3;
    private static final long CHECK_TIMEOUT_MS = 10_000;

    private MockPrefs prefs;
    private final List<Button> chips = new ArrayList<>();
    private final Handler handler = new Handler(Looper.getMainLooper());

    private View statusDot, setupPanel;
    private TextView statusTitle, statusDetail, errorMsg, customMsg, checkResult;
    private Button toggle;
    private EditText customInput;
    private LocationListener checkListener;

    private final MockService.Listener stateListener = err -> {
        if (err != null) showError(err);
        refresh();
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        prefs = new MockPrefs(this);

        statusDot = findViewById(R.id.statusDot);
        statusTitle = findViewById(R.id.statusTitle);
        statusDetail = findViewById(R.id.statusDetail);
        errorMsg = findViewById(R.id.errorMsg);
        setupPanel = findViewById(R.id.setupPanel);
        toggle = findViewById(R.id.toggle);
        customInput = findViewById(R.id.customInput);
        customMsg = findViewById(R.id.customMsg);
        checkResult = findViewById(R.id.checkResult);

        buildPlaceGrid(findViewById(R.id.placeGrid));

        toggle.setOnClickListener(v -> onToggle());
        findViewById(R.id.openDev).setOnClickListener(v -> openDeveloperOptions());
        findViewById(R.id.openAbout).setOnClickListener(v ->
                openSettings(Settings.ACTION_DEVICE_INFO_SETTINGS));
        findViewById(R.id.customSet).setOnClickListener(v -> applyCustom());
        customInput.setOnEditorActionListener((v, actionId, e) -> {
            if (actionId == EditorInfo.IME_ACTION_DONE) {
                applyCustom();
                return true;
            }
            return false;
        });
        findViewById(R.id.check).setOnClickListener(v -> onCheck());

        if (Places.byName(prefs.name()) == null) {
            customInput.setText(Coords.format(prefs.lat(), prefs.lon()));
        }
    }

    @Override
    protected void onStart() {
        super.onStart();
        MockService.setListener(stateListener);
        refresh();
    }

    @Override
    protected void onStop() {
        MockService.setListener(null);
        cancelCheck();
        super.onStop();
    }

    // ------------------------------------------------------------------ widok

    private void buildPlaceGrid(LinearLayout grid) {
        LinearLayout row = null;
        for (int i = 0; i < Places.ALL.length; i++) {
            if (i % COLUMNS == 0) {
                row = new LinearLayout(this);
                row.setOrientation(LinearLayout.HORIZONTAL);
                LinearLayout.LayoutParams rlp = new LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
                if (i > 0) rlp.topMargin = dp(8);
                grid.addView(row, rlp);
            }
            Places.Place p = Places.ALL[i];
            Button chip = makeChip(this, p.name);
            chip.setOnClickListener(v -> choose(p.name, p.lat, p.lon));
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, dp(46), 1f);
            if (i % COLUMNS != COLUMNS - 1) lp.rightMargin = dp(8);
            row.addView(chip, lp);
            chips.add(chip);
        }
    }

    /** Przycisk-kafelek miasta (używany też przez test zrzutu ekranu). */
    static Button makeChip(Context ctx, String text) {
        Button chip = new Button(ctx);
        chip.setText(text);
        chip.setAllCaps(false);
        chip.setTextSize(14f);
        chip.setSingleLine(true);
        chip.setPadding(0, 0, 0, 0);
        chip.setBackgroundResource(R.drawable.chip_bg);
        chip.setTextColor(ctx.getColor(R.color.text));
        chip.setStateListAnimator(null);
        return chip;
    }

    private void refresh() {
        boolean on = MockService.running;
        boolean allowed = MockEngine.isAllowed(this);
        String name = prefs.name();

        setupPanel.setVisibility(allowed || on ? View.GONE : View.VISIBLE);
        statusDot.setBackgroundTintList(ColorStateList.valueOf(
                getColor(on ? R.color.ok : R.color.off)));
        if (on) {
            statusTitle.setText(getString(R.string.status_on, name));
            statusDetail.setText(Coords.format(prefs.lat(), prefs.lon()));
            statusDetail.setTypeface(Typeface.MONOSPACE);
            errorMsg.setVisibility(View.GONE);
        } else {
            statusTitle.setText(R.string.status_off);
            statusDetail.setText(getString(R.string.status_off_detail));
            statusDetail.setTypeface(Typeface.DEFAULT);
        }
        toggle.setText(on ? R.string.btn_stop : R.string.btn_start);
        toggle.setActivated(on);

        for (Button chip : chips) {
            chip.setSelected(chip.getText().toString().equals(name));
        }
    }

    private void showError(String message) {
        errorMsg.setText(message);
        errorMsg.setVisibility(View.VISIBLE);
    }

    // ------------------------------------------------------------------ akcje

    private void onToggle() {
        errorMsg.setVisibility(View.GONE);
        if (MockService.running) {
            MockService.stop(this);
            handler.postDelayed(this::refresh, 300);
            return;
        }
        if (!MockEngine.isAllowed(this)) {
            showError(getString(R.string.err_not_allowed));
            refresh();
            ScrollView scroll = findViewById(R.id.scroll);
            scroll.post(() -> scroll.smoothScrollTo(0, setupPanel.getTop()));
            return;
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU
                && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, REQ_NOTIF);
            return; // usługę uruchomimy po odpowiedzi (z powiadomieniem albo bez)
        }
        MockService.start(this);
    }

    private void choose(String name, double lat, double lon) {
        prefs.set(name, lat, lon);
        if (MockService.running) MockService.start(this); // usługa wczyta nowe miejsce
        refresh();
        if (MockService.running) {
            statusTitle.setText(getString(R.string.status_on, name));
            statusDetail.setText(Coords.format(lat, lon));
        }
    }

    private void applyCustom() {
        double[] c = Coords.parse(customInput.getText().toString());
        if (c == null) {
            customMsg.setText(R.string.custom_bad);
            customMsg.setTextColor(getColor(R.color.accent_dark));
            return;
        }
        boolean inPl = Coords.inPoland(c[0], c[1]);
        customMsg.setText(inPl ? getString(R.string.custom_help) : getString(R.string.custom_outside));
        customMsg.setTextColor(getColor(inPl ? R.color.text_dim : R.color.accent_dark));
        customInput.setText(Coords.format(c[0], c[1]));
        InputMethodManager imm = getSystemService(InputMethodManager.class);
        if (imm != null) imm.hideSoftInputFromWindow(customInput.getWindowToken(), 0);
        customInput.clearFocus();
        choose(getString(R.string.custom_name), c[0], c[1]);
    }

    private void openDeveloperOptions() {
        boolean devOn = Settings.Global.getInt(getContentResolver(),
                Settings.Global.DEVELOPMENT_SETTINGS_ENABLED, 0) == 1;
        if (!devOn) {
            Toast.makeText(this, R.string.setup_no_dev, Toast.LENGTH_LONG).show();
            openSettings(Settings.ACTION_DEVICE_INFO_SETTINGS);
            return;
        }
        openSettings(Settings.ACTION_APPLICATION_DEVELOPMENT_SETTINGS);
    }

    private void openSettings(String action) {
        try {
            startActivity(new Intent(action));
        } catch (RuntimeException e) {
            startActivity(new Intent(Settings.ACTION_SETTINGS));
        }
    }

    // ------------------------------------------------------------------ sprawdzenie

    private void onCheck() {
        if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)
                != PackageManager.PERMISSION_GRANTED
                && checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION)
                != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.ACCESS_FINE_LOCATION,
                    Manifest.permission.ACCESS_COARSE_LOCATION}, REQ_LOCATION);
            return;
        }
        runCheck();
    }

    @SuppressWarnings({"MissingPermission", "deprecation"})
    private void runCheck() {
        LocationManager lm = getSystemService(LocationManager.class);
        String provider = null;
        if (lm != null) {
            if (lm.isProviderEnabled(LocationManager.GPS_PROVIDER)) {
                provider = LocationManager.GPS_PROVIDER;
            } else if (lm.isProviderEnabled(LocationManager.NETWORK_PROVIDER)) {
                provider = LocationManager.NETWORK_PROVIDER;
            }
        }
        checkResult.setVisibility(View.VISIBLE);
        checkResult.setTextColor(getColor(R.color.text));
        if (provider == null) {
            checkResult.setText(R.string.check_none);
            return;
        }
        cancelCheck();
        checkResult.setText(R.string.check_wait);
        checkListener = new LocationListener() {
            @Override public void onLocationChanged(Location l) {
                cancelCheck();
                showCheck(l);
            }
            @Override public void onStatusChanged(String p, int s, Bundle b) { }
            @Override public void onProviderEnabled(String p) { }
            @Override public void onProviderDisabled(String p) { }
        };
        try {
            lm.requestSingleUpdate(provider, checkListener, Looper.getMainLooper());
        } catch (RuntimeException e) {
            checkListener = null;
            checkResult.setText(R.string.check_none);
            return;
        }
        handler.postDelayed(checkTimeout, CHECK_TIMEOUT_MS);
    }

    private final Runnable checkTimeout = () -> {
        cancelCheck();
        checkResult.setText(R.string.check_none);
    };

    private void cancelCheck() {
        handler.removeCallbacks(checkTimeout);
        if (checkListener != null) {
            LocationManager lm = getSystemService(LocationManager.class);
            if (lm != null) lm.removeUpdates(checkListener);
            checkListener = null;
        }
    }

    private void showCheck(Location l) {
        boolean inPl = Coords.inPoland(l.getLatitude(), l.getLongitude());
        checkResult.setText(getString(R.string.check_result,
                Coords.format(l.getLatitude(), l.getLongitude()),
                getString(inPl ? R.string.check_in_pl : R.string.check_not_pl)));
        checkResult.setTextColor(getColor(inPl ? R.color.ok : R.color.accent_dark));
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] results) {
        super.onRequestPermissionsResult(requestCode, permissions, results);
        if (requestCode == REQ_NOTIF) {
            if (MockEngine.isAllowed(this)) MockService.start(this);
        } else if (requestCode == REQ_LOCATION) {
            boolean granted = false;
            for (int r : results) granted |= r == PackageManager.PERMISSION_GRANTED;
            if (granted) {
                runCheck();
            } else {
                checkResult.setVisibility(View.VISIBLE);
                checkResult.setText(R.string.check_denied);
            }
        }
    }

    private int dp(int v) {
        return Math.round(v * getResources().getDisplayMetrics().density);
    }
}
