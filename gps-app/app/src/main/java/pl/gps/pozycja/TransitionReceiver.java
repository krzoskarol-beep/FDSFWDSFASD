package pl.gps.pozycja;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.SystemClock;

import com.google.android.gms.location.ActivityTransition;
import com.google.android.gms.location.ActivityTransitionEvent;
import com.google.android.gms.location.ActivityTransitionResult;
import com.google.android.gms.location.DetectedActivity;

/** Odbiera od usług Google zdarzenia „zaczęła się jazda” i „skończyła się jazda”. */
public class TransitionReceiver extends BroadcastReceiver {

    /** Starsze zdarzenia rozpoczęcia jazdy pomijamy (np. dostarczone z dużym opóźnieniem). */
    private static final long MAX_ENTER_EVENT_AGE_MS = 10 * 60_000L;

    @Override
    public void onReceive(Context context, Intent intent) {
        if (!ActivityTransitionResult.hasResult(intent)) return;
        ActivityTransitionResult result = ActivityTransitionResult.extractResult(intent);
        if (result == null) return;

        // Interesuje nas tylko najnowsze zdarzenie dotyczące jazdy.
        ActivityTransitionEvent latest = null;
        for (ActivityTransitionEvent e : result.getTransitionEvents()) {
            if (e.getActivityType() != DetectedActivity.IN_VEHICLE) continue;
            if (latest == null || e.getElapsedRealTimeNanos() > latest.getElapsedRealTimeNanos()) {
                latest = e;
            }
        }
        if (latest == null) return;

        boolean started = latest.getTransitionType() == ActivityTransition.ACTIVITY_TRANSITION_ENTER;
        long eventTime = latest.getElapsedRealTimeNanos() / 1_000_000L;
        long ageMs = SystemClock.elapsedRealtime() - eventTime;
        // Stan zapisujemy zawsze: usługa jazdy pyta o niego co minutę (DrivePolicy).
        AutoParking.setInVehicle(context, started);
        if (!AutoParking.isEnabled(context)) return;

        EventLog.log(context, "Usługi Google: " + (started ? "W POJEŹDZIE" : "POZA POJAZDEM")
                + " (zdarzenie sprzed " + ageMs / 1000 + " s)");

        if (started) {
            if (ageMs > MAX_ENTER_EVENT_AGE_MS) {
                EventLog.log(context, "Pominięto zbyt stare zdarzenie początku jazdy");
            } else if (!DrivingService.start(context, DrivingService.ACTION_DRIVING_STARTED,
                    DrivingService.SOURCE_ACTIVITY, eventTime)) {
                EventLog.log(context, "BŁĄD: system nie pozwolił uruchomić usługi jazdy");
                Notifications.showTrackingBlocked(context);
            }
        } else if (!DrivingService.start(context, DrivingService.ACTION_DRIVING_ENDED,
                DrivingService.SOURCE_ACTIVITY, eventTime)) {
            EventLog.log(context, "BŁĄD: system nie pozwolił uruchomić usługi, zapis awaryjny");
            Notifications.showTrackingBlocked(context);
            DrivingService.saveLastKnown(context, eventTime);
        }
    }
}
