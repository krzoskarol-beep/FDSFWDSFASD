package pl.gps.pozycja;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Path;
import android.util.AttributeSet;
import android.view.View;

/**
 * Tarcza kierunku do auta na asfaltowej karcie: żółta strzałka jak pas na jezdni,
 * podziałka co 30° i znacznik u góry tarczy, który pokazuje, gdzie jest przód telefonu.
 * Gdy auto jest tuż obok, zamiast strzałki rysujemy zielone koło z „P”.
 */
public class ArrowView extends View {

    private final Paint dialPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint ringPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint tickPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint arrowPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint markPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint letterPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Path arrow = new Path();
    private final Path mark = new Path();

    private float angle;
    private boolean visible;
    private boolean arrived;

    public ArrowView(Context context, AttributeSet attrs) {
        super(context, attrs);
        float dp = getResources().getDisplayMetrics().density;
        dialPaint.setColor(context.getColor(R.color.asphalt_raised));
        ringPaint.setStyle(Paint.Style.STROKE);
        ringPaint.setStrokeWidth(1.5f * dp);
        ringPaint.setColor(context.getColor(R.color.on_asphalt_line));
        tickPaint.setStrokeWidth(2f * dp);
        tickPaint.setStrokeCap(Paint.Cap.ROUND);
        tickPaint.setColor(context.getColor(R.color.on_asphalt_line));
        arrowPaint.setColor(context.getColor(R.color.lane_yellow));
        markPaint.setColor(context.getColor(R.color.on_asphalt_soft));
        letterPaint.setColor(context.getColor(R.color.asphalt));
        letterPaint.setTextAlign(Paint.Align.CENTER);
        letterPaint.setFakeBoldText(true);
        setImportantForAccessibility(IMPORTANT_FOR_ACCESSIBILITY_YES);
    }

    /** @param degrees obrót strzałki zgodnie z ruchem wskazówek zegara, 0 = do góry ekranu */
    public void setAngle(float degrees) {
        angle = degrees;
        visible = true;
        invalidate();
    }

    public void hideArrow() {
        visible = false;
        invalidate();
    }

    /** Samochód jest tuż obok: zamiast strzałki rysujemy zielone koło z „P”. */
    public void setArrived(boolean arrived) {
        if (this.arrived != arrived) {
            this.arrived = arrived;
            invalidate();
        }
    }

    @Override
    protected void onSizeChanged(int w, int h, int oldw, int oldh) {
        float cx = w / 2f, cy = h / 2f, r = Math.min(w, h) / 2f;
        // Strzałka nawigacyjna: smukły grot z wcięciem u podstawy.
        arrow.reset();
        arrow.moveTo(cx, cy - r * 0.62f);
        arrow.lineTo(cx + r * 0.34f, cy + r * 0.42f);
        arrow.lineTo(cx, cy + r * 0.22f);
        arrow.lineTo(cx - r * 0.34f, cy + r * 0.42f);
        arrow.close();
        // Znacznik „przód telefonu” na górnej krawędzi tarczy.
        mark.reset();
        mark.moveTo(cx, cy - r * 0.97f);
        mark.lineTo(cx + r * 0.07f, cy - r * 0.84f);
        mark.lineTo(cx - r * 0.07f, cy - r * 0.84f);
        mark.close();
        letterPaint.setTextSize(r * 0.5f);
    }

    @Override
    protected void onDraw(Canvas canvas) {
        float cx = getWidth() / 2f, cy = getHeight() / 2f, r = Math.min(getWidth(), getHeight()) / 2f;
        canvas.drawCircle(cx, cy, r, dialPaint);
        canvas.drawCircle(cx, cy, r * 0.78f, ringPaint);
        for (int i = 0; i < 12; i++) {
            if (i == 0) continue; // u góry jest znacznik przodu telefonu
            double a = Math.toRadians(i * 30);
            float sin = (float) Math.sin(a), cos = (float) Math.cos(a);
            canvas.drawLine(cx + sin * r * 0.86f, cy - cos * r * 0.86f,
                    cx + sin * r * 0.93f, cy - cos * r * 0.93f, tickPaint);
        }
        canvas.drawPath(mark, markPaint);

        if (arrived) {
            arrowPaint.setColor(getContext().getColor(R.color.arrived));
            canvas.drawCircle(cx, cy, r * 0.42f, arrowPaint);
            Paint.FontMetrics fm = letterPaint.getFontMetrics();
            canvas.drawText("P", cx, cy - (fm.ascent + fm.descent) / 2f, letterPaint);
            arrowPaint.setColor(getContext().getColor(R.color.lane_yellow));
            return;
        }
        if (!visible) return;

        canvas.save();
        canvas.rotate(angle, cx, cy);
        canvas.drawPath(arrow, arrowPaint);
        canvas.restore();
    }
}
