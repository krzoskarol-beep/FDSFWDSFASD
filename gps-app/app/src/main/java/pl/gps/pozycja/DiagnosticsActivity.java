package pl.gps.pozycja;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.os.PowerManager;
import android.text.TextUtils;
import android.widget.TextView;

import java.util.List;

/**
 * Ekran „Diagnostyka”: stan uprawnień i ustawień telefonu oraz dziennik zdarzeń z tła.
 * Pozwala sprawdzić, dlaczego parking się nie zapisał, i udostępnić te informacje.
 */
public class DiagnosticsActivity extends Activity {

    private TextView status, log;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_diagnostics);
        status = findViewById(R.id.diagStatus);
        log = findViewById(R.id.diagLog);

        findViewById(R.id.diagRefresh).setOnClickListener(v -> refresh());
        findViewById(R.id.diagShare).setOnClickListener(v -> share());
        findViewById(R.id.diagClear).setOnClickListener(v -> new AlertDialog.Builder(this)
                .setTitle(R.string.diag_clear_confirm)
                .setPositiveButton(R.string.diag_clear, (d, w) -> {
                    EventLog.clear(this);
                    refresh();
                })
                .setNegativeButton(R.string.parking_dialog_cancel, null)
                .show());

        MainActivity.applySystemBarInsets(findViewById(R.id.root));
    }

    @Override
    protected void onResume() {
        super.onResume();
        refresh();
    }

    private void refresh() {
        status.setText(statusText());
        List<String> entries = EventLog.read(this);
        log.setText(entries.isEmpty() ? getString(R.string.diag_log_empty) : TextUtils.join("\n", entries));
    }

    private String statusText() {
        StringBuilder sb = new StringBuilder();
        line(sb, "Aplikacja", versionName());
        line(sb, "Telefon", Build.MANUFACTURER + " " + Build.MODEL);
        line(sb, "Android", Build.VERSION.RELEASE + " (API " + Build.VERSION.SDK_INT + ")");
        line(sb, "Usługi Google Play", yesNo(AutoParking.isPlayServicesAvailable(this)));
        line(sb, "Automatyczny zapis", AutoParking.isEnabled(this) ? "włączony" : "wyłączony");
        line(sb, "Usługa jazdy", DrivingService.running
                ? (DrivingService.driving ? "działa (jazda)" : "działa") : "nie działa");
        line(sb, "Lokalizacja dokładna", yesNo(granted(Manifest.permission.ACCESS_FINE_LOCATION)));
        line(sb, "Lokalizacja w tle", yesNo(AutoParking.hasBackgroundLocationPermission(this)));
        line(sb, "Aktywność fizyczna", yesNo(AutoParking.hasActivityRecognitionPermission(this)));
        line(sb, "Powiadomienia", yesNo(Notifications.canPost(this)));
        PowerManager pm = getSystemService(PowerManager.class);
        line(sb, "Bez optymalizacji baterii",
                yesNo(pm != null && pm.isIgnoringBatteryOptimizations(getPackageName())));
        if (pm != null) line(sb, "Oszczędzanie energii", pm.isPowerSaveMode() ? "WŁĄCZONE" : "wyłączone");
        return sb.toString().trim();
    }

    private static void line(StringBuilder sb, String label, String value) {
        sb.append(label).append(": ").append(value).append('\n');
    }

    private static String yesNo(boolean b) {
        return b ? "tak" : "NIE";
    }

    private boolean granted(String permission) {
        return checkSelfPermission(permission) == PackageManager.PERMISSION_GRANTED;
    }

    @SuppressWarnings("deprecation")
    private String versionName() {
        try {
            PackageInfo pi = getPackageManager().getPackageInfo(getPackageName(), 0);
            return pi.versionName + " (" + pi.versionCode + ")";
        } catch (PackageManager.NameNotFoundException e) {
            return "?";
        }
    }

    private void share() {
        String text = getString(R.string.app_name) + " – diagnostyka\n\n" + statusText()
                + "\n\n" + TextUtils.join("\n", EventLog.read(this));
        Intent send = new Intent(Intent.ACTION_SEND)
                .setType("text/plain")
                .putExtra(Intent.EXTRA_SUBJECT, getString(R.string.diag_title))
                .putExtra(Intent.EXTRA_TEXT, text);
        startActivity(Intent.createChooser(send, getString(R.string.share)));
    }
}
