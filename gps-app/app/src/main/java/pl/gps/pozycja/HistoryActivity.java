package pl.gps.pozycja;

import android.app.Activity;
import android.content.Context;
import android.app.AlertDialog;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.text.format.DateUtils;
import android.view.View;
import android.widget.ListView;
import android.widget.SimpleAdapter;
import android.widget.Toast;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * Historia ostatnich miejsc parkowania. Dotknięcie otwiera miejsce w mapach,
 * przytrzymanie pozwala przywrócić je jako aktualne (np. gdy automat zapisał
 * przystanek autobusowy) albo usunąć z historii.
 */
public class HistoryActivity extends Activity {

    private ParkingStore store;
    private ListView list;
    private View empty;
    private List<ParkingStore.Spot> spots = new ArrayList<>();

    @Override
    protected void attachBaseContext(Context base) {
        // Motyw wybrany w aplikacji (systemowy / jasny / ciemny), patrz ThemePrefs.
        super.attachBaseContext(ThemePrefs.wrap(base));
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_history);
        Fonts.apply(findViewById(R.id.root));
        store = new ParkingStore(this);
        list = findViewById(R.id.historyList);
        empty = findViewById(R.id.historyEmpty);

        list.setOnItemClickListener((p, v, pos, id) -> openInMaps(spots.get(pos)));
        list.setOnItemLongClickListener((p, v, pos, id) -> {
            showActions(spots.get(pos));
            return true;
        });
        findViewById(R.id.historyClear).setOnClickListener(v -> new AlertDialog.Builder(this)
                .setTitle(R.string.history_clear_confirm)
                .setPositiveButton(R.string.history_clear, (d, w) -> {
                    store.clearHistory();
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
        spots = store.history();
        ParkingStore.Spot current = store.load();
        List<Map<String, String>> rows = new ArrayList<>();
        for (ParkingStore.Spot s : spots) {
            Map<String, String> row = new HashMap<>();
            String when = DateUtils.formatDateTime(this, s.savedAt,
                    DateUtils.FORMAT_SHOW_DATE | DateUtils.FORMAT_SHOW_TIME | DateUtils.FORMAT_ABBREV_MONTH);
            boolean isCurrent = current != null && current.savedAt == s.savedAt;
            row.put("title", (isCurrent ? getString(R.string.history_current) + " " : "") + when);
            row.put("subtitle", describe(s));
            rows.add(row);
        }
        list.setAdapter(new SimpleAdapter(this, rows, android.R.layout.simple_list_item_2,
                new String[]{"title", "subtitle"}, new int[]{android.R.id.text1, android.R.id.text2}) {
            @Override
            public View getView(int position, View convertView, android.view.ViewGroup parent) {
                View v = super.getView(position, convertView, parent);
                ((android.widget.TextView) v.findViewById(android.R.id.text1)).setTypeface(null, android.graphics.Typeface.BOLD);
                Fonts.apply(v); // wiersze powstają po ustawieniu fontu na ekranie
                v.setPadding(v.getPaddingLeft(), dp(12), v.getPaddingRight(), dp(12));
                return v;
            }
        });
        empty.setVisibility(spots.isEmpty() ? View.VISIBLE : View.GONE);
        findViewById(R.id.historyClear).setVisibility(spots.isEmpty() ? View.GONE : View.VISIBLE);
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private String describe(ParkingStore.Spot s) {
        StringBuilder sb = new StringBuilder();
        sb.append(s.address.isEmpty()
                ? String.format(Locale.US, "%.5f, %.5f", s.latitude, s.longitude) : s.address);
        if (!s.note.isEmpty()) sb.append("\n").append(s.note);
        if (s.accuracy > 0) sb.append(String.format(Locale.getDefault(), "  (± %.0f m)", s.accuracy));
        return sb.toString();
    }

    private void showActions(ParkingStore.Spot s) {
        new AlertDialog.Builder(this)
                .setTitle(describe(s))
                .setItems(new CharSequence[]{getString(R.string.history_restore),
                        getString(R.string.open_maps), getString(R.string.history_delete)}, (d, which) -> {
                    if (which == 0) {
                        store.restore(s);
                        EventLog.log(this, "Przywrócono miejsce z historii");
                        Toast.makeText(this, R.string.history_restored, Toast.LENGTH_SHORT).show();
                        finish();
                    } else if (which == 1) {
                        openInMaps(s);
                    } else {
                        store.removeFromHistory(s.savedAt);
                        refresh();
                    }
                })
                .show();
    }

    private void openInMaps(ParkingStore.Spot s) {
        String c = String.format(Locale.US, "%.6f,%.6f", s.latitude, s.longitude);
        Uri geo = Uri.parse("geo:" + c + "?q=" + c + "(" + Uri.encode(getString(R.string.parking_label)) + ")");
        try {
            startActivity(new Intent(Intent.ACTION_VIEW, geo));
        } catch (ActivityNotFoundException e) {
            try {
                startActivity(new Intent(Intent.ACTION_VIEW,
                        Uri.parse("https://maps.google.com/?q=" + c)));
            } catch (ActivityNotFoundException e2) {
                Toast.makeText(this, R.string.no_maps_app, Toast.LENGTH_SHORT).show();
            }
        }
    }
}
