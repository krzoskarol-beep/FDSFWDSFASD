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
        if (!AutoParking.isEnabled(context) || !ActivityTransitionResult.hasResult(intent)) return;
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
        long ageMs = (SystemClock.elapsedRealtimeNanos() - latest.getElapsedRealTimeNanos()) / 1_000_000L;

        if (started) {
            if (ageMs <= MAX_ENTER_EVENT_AGE_MS) {
                DrivingService.start(context, DrivingService.ACTION_DRIVING_STARTED);
            }
        } else if (!DrivingService.start(context, DrivingService.ACTION_DRIVING_ENDED)) {
            // System nie pozwolił uruchomić usługi: zapisz ostatnią znaną pozycję.
            DrivingService.saveLastKnown(context);
        }
    }
}
