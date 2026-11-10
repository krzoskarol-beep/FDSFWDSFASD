package pl.gps.pozycja;

import android.app.Activity;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.os.Build;
import android.view.Display;
import android.view.Surface;

/**
 * Kompas: podaje, w którą stronę świata skierowana jest góra telefonu (azymut względem
 * północy magnetycznej). Używa czujnika orientacji (rotation vector), a gdy go brak,
 * akcelerometru z magnetometrem.
 */
final class Compass implements SensorEventListener {

    interface Listener {
        /** @param azimuthDegrees 0–360°, względem północy magnetycznej */
        void onAzimuthChanged(float azimuthDegrees);

        /** @param needsCalibration true, gdy magnetometr podaje niewiarygodne dane */
        void onCalibrationChanged(boolean needsCalibration);
    }

    /** Wygładzanie drgań strzałki: im mniej, tym spokojniej, ale wolniej. */
    private static final float SMOOTHING = 0.15f;

    private final Activity activity;
    private final Listener listener;
    private final SensorManager sensors;
    private final Sensor rotationVector, accelerometer, magnetometer;

    private final float[] rotation = new float[9];
    private final float[] remapped = new float[9];
    private final float[] orientation = new float[3];
    private float[] gravity, geomagnetic;
    private double smoothSin, smoothCos;
    private boolean hasValue, running;

    Compass(Activity activity, Listener listener) {
        this.activity = activity;
        this.listener = listener;
        sensors = (SensorManager) activity.getSystemService(Activity.SENSOR_SERVICE);
        rotationVector = sensors.getDefaultSensor(Sensor.TYPE_ROTATION_VECTOR);
        accelerometer = sensors.getDefaultSensor(Sensor.TYPE_ACCELEROMETER);
        magnetometer = sensors.getDefaultSensor(Sensor.TYPE_MAGNETIC_FIELD);
    }

    boolean isAvailable() {
        return rotationVector != null || (accelerometer != null && magnetometer != null);
    }

    void start() {
        if (running || !isAvailable()) return;
        running = true;
        hasValue = false;
        if (rotationVector != null) {
            sensors.registerListener(this, rotationVector, SensorManager.SENSOR_DELAY_UI);
        } else {
            sensors.registerListener(this, accelerometer, SensorManager.SENSOR_DELAY_UI);
        }
        // Magnetometr słuchamy też przy rotation vector, żeby wiedzieć, czy wymaga kalibracji.
        if (magnetometer != null) {
            sensors.registerListener(this, magnetometer, SensorManager.SENSOR_DELAY_UI);
        }
    }

    void stop() {
        if (!running) return;
        running = false;
        sensors.unregisterListener(this);
    }

    @Override
    public void onSensorChanged(SensorEvent event) {
        int type = event.sensor.getType();
        if (type == Sensor.TYPE_ROTATION_VECTOR) {
            SensorManager.getRotationMatrixFromVector(rotation, event.values);
        } else if (type == Sensor.TYPE_ACCELEROMETER) {
            gravity = event.values.clone();
            if (geomagnetic == null || !SensorManager.getRotationMatrix(rotation, null, gravity, geomagnetic)) {
                return;
            }
        } else if (type == Sensor.TYPE_MAGNETIC_FIELD) {
            geomagnetic = event.values.clone();
            return; // azymut liczymy przy następnym odczycie akcelerometru / rotation vector
        } else {
            return;
        }
        publish();
    }

    private void publish() {
        // Uwzględnij obrót ekranu (telefon trzymany poziomo).
        int axisX = SensorManager.AXIS_X, axisY = SensorManager.AXIS_Y;
        switch (displayRotation()) {
            case Surface.ROTATION_90:
                axisX = SensorManager.AXIS_Y; axisY = SensorManager.AXIS_MINUS_X; break;
            case Surface.ROTATION_180:
                axisX = SensorManager.AXIS_MINUS_X; axisY = SensorManager.AXIS_MINUS_Y; break;
            case Surface.ROTATION_270:
                axisX = SensorManager.AXIS_MINUS_Y; axisY = SensorManager.AXIS_X; break;
            default:
                break;
        }
        SensorManager.remapCoordinateSystem(rotation, axisX, axisY, remapped);
        SensorManager.getOrientation(remapped, orientation);
        double azimuth = orientation[0]; // radiany, -π..π

        // Wygładzanie na okręgu (żeby przejście 359° → 0° nie kręciło strzałką dookoła).
        if (!hasValue) {
            smoothSin = Math.sin(azimuth);
            smoothCos = Math.cos(azimuth);
            hasValue = true;
        } else {
            smoothSin += SMOOTHING * (Math.sin(azimuth) - smoothSin);
            smoothCos += SMOOTHING * (Math.cos(azimuth) - smoothCos);
        }
        double deg = Math.toDegrees(Math.atan2(smoothSin, smoothCos));
        listener.onAzimuthChanged((float) Geo.normalizeDegrees(deg));
    }

    @SuppressWarnings("deprecation")
    private int displayRotation() {
        Display d = Build.VERSION.SDK_INT >= 30
                ? activity.getDisplay()
                : activity.getWindowManager().getDefaultDisplay();
        return d == null ? Surface.ROTATION_0 : d.getRotation();
    }

    @Override
    public void onAccuracyChanged(Sensor sensor, int accuracy) {
        if (sensor.getType() == Sensor.TYPE_MAGNETIC_FIELD) {
            listener.onCalibrationChanged(accuracy == SensorManager.SENSOR_STATUS_UNRELIABLE
                    || accuracy == SensorManager.SENSOR_STATUS_ACCURACY_LOW);
        }
    }
}
