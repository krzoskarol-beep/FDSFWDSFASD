package pl.korektor.dzwiek;

import android.Manifest;
import android.app.Activity;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.ServiceConnection;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.os.IBinder;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.CompoundButton;
import android.widget.LinearLayout;
import android.widget.SeekBar;
import android.widget.Switch;
import android.widget.TextView;

import java.util.ArrayList;
import java.util.List;

/**
 * Ekran korektora: główny przełącznik, zestawy (presety), fadery pasm oraz suwaki
 * basu i przestrzeni. Źródłem prawdy o ustawieniach jest {@link EqPrefs}; gdy korektor
 * jest włączony, zmiany trafiają na żywo do silnika w usłudze {@link EqService}.
 */
public class EqActivity extends Activity {

    private EqEngine meta;           // tylko do odczytu struktury pasm/presetów (nigdy nie włączany)
    private EqPrefs prefs;

    private Switch master;
    private TextView statusMsg;
    private LinearLayout presetRow, faderRow, bassPanel, surroundPanel;
    private SeekBar bass, surround;
    private Button btnReset;

    private FaderView[] faders = new FaderView[0];
    private TextView[] dbLabels = new TextView[0];
    private final List<Button> presetChips = new ArrayList<>();

    private short bandCount, minLevel, maxLevel;
    private short selectedPreset = EqPrefs.PRESET_CUSTOM;
    private short[] levels = new short[0];

    private EqService service;
    private boolean bound;

    private final ServiceConnection conn = new ServiceConnection() {
        @Override public void onServiceConnected(ComponentName name, IBinder binder) {
            service = ((EqService.LocalBinder) binder).service();
            bound = true;
            // Zsynchronizuj na wypadek zmian zrobionych, zanim usługa się podłączyła.
            service.applyFromPrefs();
        }
        @Override public void onServiceDisconnected(ComponentName name) {
            service = null;
            bound = false;
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_eq);
        prefs = new EqPrefs(this);
        meta = new EqEngine();

        master = findViewById(R.id.master);
        statusMsg = findViewById(R.id.statusMsg);
        presetRow = findViewById(R.id.presetRow);
        faderRow = findViewById(R.id.faderRow);
        bass = findViewById(R.id.bass);
        surround = findViewById(R.id.surround);
        bassPanel = findViewById(R.id.bassPanel);
        surroundPanel = findViewById(R.id.surroundPanel);
        btnReset = findViewById(R.id.btnReset);

        if (!meta.supported) {
            showUnsupported();
            return;
        }

        bandCount = meta.bandCount();
        minLevel = meta.minLevel();
        maxLevel = meta.maxLevel();
        loadLevels();

        buildPresets();
        buildFaders();
        setupBassSurround();

        btnReset.setOnClickListener(v -> resetAll());

        master.setChecked(prefs.isEnabled());
        master.setOnCheckedChangeListener((CompoundButton b, boolean on) -> onMasterToggled(on));

        if (prefs.isEnabled()) {
            startEngine();
        }
        refreshEditable();
    }

    @Override
    protected void onDestroy() {
        if (bound) {
            try { unbindService(conn); } catch (IllegalArgumentException ignored) {}
            bound = false;
        }
        if (meta != null) {
            meta.release();   // nigdy nie był włączony, więc dźwięku nie zmienia
            meta = null;
        }
        super.onDestroy();
    }

    // ------------------------------------------------------------------ budowa UI
    private void loadLevels() {
        short[] saved = prefs.bandLevels();
        levels = new short[bandCount];
        if (saved != null) {
            for (int i = 0; i < bandCount && i < saved.length; i++) levels[i] = saved[i];
        }
        selectedPreset = prefs.preset();
    }

    private void buildPresets() {
        presetChips.clear();
        presetRow.removeAllViews();
        short count = meta.presetCount();
        for (short p = 0; p < count; p++) {
            addChip(meta.presetName(p), p);
        }
        addChip(getString(R.string.custom_preset), EqPrefs.PRESET_CUSTOM);
        updateChipSelection();
    }

    private void addChip(String text, short preset) {
        Button chip = new Button(this);
        chip.setText(text);
        chip.setAllCaps(false);
        chip.setTextSize(14f);
        chip.setBackgroundResource(R.drawable.chip_bg);
        chip.setTextColor(getColorStateList(R.color.chip_text));
        chip.setStateListAnimator(null);
        chip.setMinimumHeight(dp(40));
        chip.setMinimumWidth(0);
        chip.setPadding(dp(18), 0, dp(18), 0);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, dp(40));
        lp.rightMargin = dp(8);
        chip.setLayoutParams(lp);
        chip.setOnClickListener(v -> selectPreset(preset));
        presetRow.addView(chip);
        presetChips.add(chip);
    }

    private void buildFaders() {
        faderRow.removeAllViews();
        faders = new FaderView[bandCount];
        dbLabels = new TextView[bandCount];
        for (short b = 0; b < bandCount; b++) {
            final short band = b;
            LinearLayout col = new LinearLayout(this);
            col.setOrientation(LinearLayout.VERTICAL);
            col.setGravity(Gravity.CENTER_HORIZONTAL);
            LinearLayout.LayoutParams colLp = new LinearLayout.LayoutParams(0,
                    ViewGroup.LayoutParams.MATCH_PARENT, 1f);
            col.setLayoutParams(colLp);

            TextView db = new TextView(this);
            db.setText(EqMath.formatDb(levels[band]));
            db.setTextColor(getColor(R.color.text_dim));
            db.setTextSize(11f);
            db.setGravity(Gravity.CENTER);
            db.setTypeface(android.graphics.Typeface.MONOSPACE);
            col.addView(db, new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

            FaderView fader = new FaderView(this, null);
            fader.setFraction(EqMath.levelToFraction(levels[band], minLevel, maxLevel));
            fader.setOnFractionChanged((v, fraction, fromUser) -> {
                if (!fromUser) return;
                short level = EqMath.fractionToLevel(fraction, minLevel, maxLevel);
                onBandChanged(band, level);
            });
            LinearLayout.LayoutParams fLp = new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f);
            fLp.topMargin = dp(6);
            fLp.bottomMargin = dp(6);
            col.addView(fader, fLp);

            TextView freq = new TextView(this);
            freq.setText(EqMath.formatFreq(meta.centerFreqHz(band)));
            freq.setTextColor(getColor(R.color.text_dim));
            freq.setTextSize(11f);
            freq.setGravity(Gravity.CENTER);
            freq.setTypeface(android.graphics.Typeface.MONOSPACE);
            col.addView(freq, new LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

            faderRow.addView(col);
            faders[band] = fader;
            dbLabels[band] = db;
        }
    }

    private void setupBassSurround() {
        bass.setProgress(prefs.bass());
        surround.setProgress(prefs.virtualizer());
        bassPanel.setVisibility(meta.bassSupported ? View.VISIBLE : View.GONE);
        surroundPanel.setVisibility(meta.virtualizerSupported ? View.VISIBLE : View.GONE);

        bass.setOnSeekBarChangeListener(new SimpleSeek() {
            @Override public void onProgressChanged(SeekBar sb, int p, boolean user) {
                if (!user) return;
                prefs.setBass(p);
                if (liveEngine() != null) liveEngine().setBassStrength(p);
            }
        });
        surround.setOnSeekBarChangeListener(new SimpleSeek() {
            @Override public void onProgressChanged(SeekBar sb, int p, boolean user) {
                if (!user) return;
                prefs.setVirtualizer(p);
                if (liveEngine() != null) liveEngine().setVirtualizerStrength(p);
            }
        });
    }

    // ------------------------------------------------------------------ zmiany ustawień
    private void onBandChanged(short band, short level) {
        levels[band] = level;
        dbLabels[band].setText(EqMath.formatDb(level));
        selectedPreset = EqPrefs.PRESET_CUSTOM;
        prefs.setPreset(EqPrefs.PRESET_CUSTOM);
        prefs.setBandLevels(levels);
        updateChipSelection();
        if (liveEngine() != null) liveEngine().setBandLevel(band, level);
    }

    private void selectPreset(short preset) {
        selectedPreset = preset;
        if (preset != EqPrefs.PRESET_CUSTOM) {
            meta.usePreset(preset);
            for (short b = 0; b < bandCount; b++) {
                levels[b] = meta.bandLevel(b);
                faders[b].setFraction(EqMath.levelToFraction(levels[b], minLevel, maxLevel));
                dbLabels[b].setText(EqMath.formatDb(levels[b]));
            }
            if (liveEngine() != null) liveEngine().usePreset(preset);
        }
        prefs.setPreset(preset);
        prefs.setBandLevels(levels);
        updateChipSelection();
    }

    private void resetAll() {
        for (short b = 0; b < bandCount; b++) {
            levels[b] = 0;
            faders[b].setFraction(EqMath.levelToFraction((short) 0, minLevel, maxLevel));
            dbLabels[b].setText(EqMath.formatDb((short) 0));
            if (liveEngine() != null) liveEngine().setBandLevel(b, (short) 0);
        }
        bass.setProgress(0);
        surround.setProgress(0);
        selectedPreset = EqPrefs.PRESET_CUSTOM;
        prefs.setPreset(EqPrefs.PRESET_CUSTOM);
        prefs.setBandLevels(levels);
        prefs.setBass(0);
        prefs.setVirtualizer(0);
        if (liveEngine() != null) {
            liveEngine().setBassStrength(0);
            liveEngine().setVirtualizerStrength(0);
        }
        updateChipSelection();
    }

    private void updateChipSelection() {
        for (int i = 0; i < presetChips.size(); i++) {
            boolean isCustomChip = (i == presetChips.size() - 1);
            short chipPreset = isCustomChip ? EqPrefs.PRESET_CUSTOM : (short) i;
            presetChips.get(i).setSelected(chipPreset == selectedPreset);
        }
    }

    // ------------------------------------------------------------------ główny przełącznik
    private void onMasterToggled(boolean on) {
        prefs.setEnabled(on);
        if (on) {
            requestNotificationPermissionIfNeeded();
            startEngine();
        } else {
            stopEngine();
        }
        refreshEditable();
    }

    private void startEngine() {
        EqService.start(this);
        try {
            bindService(new Intent(this, EqService.class), conn, 0);
        } catch (RuntimeException ignored) {}
    }

    private void stopEngine() {
        if (bound) {
            try { unbindService(conn); } catch (IllegalArgumentException ignored) {}
            bound = false;
        }
        service = null;
        EqService.stop(this);
    }

    /** Silnik usługi, gdy korektor jest włączony i podłączony; inaczej null. */
    private EqEngine liveEngine() {
        return (bound && service != null) ? service.engine() : null;
    }

    private void refreshEditable() {
        boolean on = master.isChecked();
        for (FaderView f : faders) f.setEnabledLook(on);
        for (Button c : presetChips) { c.setEnabled(on); c.setAlpha(on ? 1f : 0.4f); }
        bass.setEnabled(on);
        surround.setEnabled(on);
        btnReset.setEnabled(on);
        btnReset.setAlpha(on ? 1f : 0.4f);
        bass.setAlpha(on ? 1f : 0.4f);
        surround.setAlpha(on ? 1f : 0.4f);
        statusMsg.setVisibility(on ? View.GONE : View.VISIBLE);
        statusMsg.setText(R.string.enable_to_edit);
    }

    private void showUnsupported() {
        statusMsg.setVisibility(View.VISIBLE);
        statusMsg.setText(R.string.unsupported);
        master.setEnabled(false);
        presetRow.setVisibility(View.GONE);
        faderRow.setVisibility(View.GONE);
        bassPanel.setVisibility(View.GONE);
        surroundPanel.setVisibility(View.GONE);
        btnReset.setVisibility(View.GONE);
    }

    private void requestNotificationPermissionIfNeeded() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU
                && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, 1);
        }
    }

    private int dp(int v) {
        return Math.round(v * getResources().getDisplayMetrics().density);
    }

    /** SeekBar listener z pustymi start/stop, by nie powtarzać kodu. */
    private abstract static class SimpleSeek implements SeekBar.OnSeekBarChangeListener {
        @Override public void onStartTrackingTouch(SeekBar seekBar) {}
        @Override public void onStopTrackingTouch(SeekBar seekBar) {}
    }
}
