
import streamlit as st
import numpy as np
import soundfile as sf
import matplotlib.pyplot as plt
import hashlib
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet

st.set_page_config(
    page_title="Digital Forensics of Audio",
    page_icon="🔍",
    layout="wide"
)

st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #0b1220, #111d30);
    color: #f1f5f9;
}
h1, h2, h3 { color: #5eead4; }
div[data-testid="stMetric"] {
    background: #17263b;
    border: 1px solid #29445c;
    padding: 16px;
    border-radius: 12px;
}
.stButton button, .stDownloadButton button {
    background: #0d9488;
    color: white;
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)

st.title("🔍 Digital Forensics of Audio")
st.caption("Audio metadata • SHA-256 integrity checking • Signal analysis • PDF reports")

st.info(
    "Upload WAV, FLAC, or OGG audio files for analysis. "
    "This tool provides technical indicators, not definitive proof of tampering."
)

def sha256(data):
    return hashlib.sha256(data).hexdigest()

def load_audio(uploaded):
    data = uploaded.getvalue()
    audio, sample_rate = sf.read(
        io.BytesIO(data), dtype="float32", always_2d=True
    )
    return data, audio, sample_rate

def audio_metrics(audio, sample_rate):
    mono = audio.mean(axis=1)
    peak = float(np.max(np.abs(mono))) if len(mono) else 0.0
    rms = float(np.sqrt(np.mean(mono ** 2))) if len(mono) else 0.0
    duration = len(mono) / sample_rate if sample_rate else 0.0

    frame_length = max(1, int(sample_rate * 0.05))
    frame_rms = []
    for start in range(0, len(mono), frame_length):
        frame = mono[start:start + frame_length]
        if len(frame):
            frame_rms.append(float(np.sqrt(np.mean(frame ** 2))))

    threshold = max(1e-6, peak * 0.01)
    low_energy_frames = sum(value < threshold for value in frame_rms)

    abrupt_changes = (
        int(np.sum(np.abs(np.diff(mono)) > 0.1))
        if len(mono) > 1 else 0
    )

    return {
        "Duration (seconds)": round(duration, 3),
        "Sample rate (Hz)": int(sample_rate),
        "Channels": int(audio.shape[1]),
        "Peak amplitude": round(peak, 6),
        "RMS energy": round(rms, 6),
        "Low-energy frames (50 ms)": int(low_energy_frames),
        "Abrupt sample changes": abrupt_changes,
    }, mono, frame_rms

def make_pdf(filename, digest, metrics, comparison=None):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Digital Forensics of Audio", styles["Title"]),
        Spacer(1, 12),
        Paragraph("Audio Analysis Report", styles["Heading2"]),
        Spacer(1, 8),
        Paragraph(f"Filename: {filename}", styles["Normal"]),
        Spacer(1, 8),
        Paragraph("SHA-256 Hash", styles["Heading3"]),
        Paragraph(digest, styles["Normal"]),
        Spacer(1, 14),
        Paragraph("Technical Analysis", styles["Heading2"]),
        Spacer(1, 8),
    ]

    table_data = [["Metric", "Result"]]
    table_data += [[key, str(value)] for key, value in metrics.items()]
    table = Table(table_data, colWidths=[250, 220])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0D9488")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("PADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(table)
    if comparison:
        story += [
            Spacer(1, 14),
            Paragraph("File Comparison", styles["Heading2"]),
            Paragraph(comparison, styles["Normal"]),
        ]
    story += [
        Spacer(1, 18),
        Paragraph(
            "Note: These measurements are technical indicators only. "
            "They do not independently prove editing, tampering, or authenticity.",
            styles["Italic"]
        )
    ]
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

tab1, tab2 = st.tabs(["🎧 Analyze Audio", "⚖️ Compare Audio Files"])

with tab1:
    uploaded = st.file_uploader(
        "Choose an audio file",
        type=["wav", "flac", "ogg"],
        key="single_audio"
    )

    if uploaded is not None:
        try:
            data, audio, sample_rate = load_audio(uploaded)
            metrics, mono, frame_rms = audio_metrics(audio, sample_rate)
            digest = sha256(data)

            st.subheader("Audio Overview")
            c1, c2, c3 = st.columns(3)
            c1.metric("Duration", f"{metrics['Duration (seconds)']} s")
            c2.metric("Sample Rate", f"{sample_rate:,} Hz")
            c3.metric("Channels", str(audio.shape[1]))

            st.subheader("File Integrity")
            st.write("**SHA-256 hash**")
            st.code(digest)
            st.caption(
                "A hash identifies the exact file bytes. Matching hashes indicate "
                "byte-for-byte equality; a different hash only means the files differ."
            )

            st.subheader("Technical Metadata")
            st.dataframe(
                [{"Metric": key, "Value": value}
                 for key, value in metrics.items()],
                use_container_width=True,
                hide_index=True
            )

            st.subheader("Audio Waveform")
            times = np.arange(len(mono)) / sample_rate
            max_points = 100000
            step = max(1, len(mono) // max_points)
            fig, ax = plt.subplots(figsize=(12, 3))
            ax.plot(times[::step], mono[::step], linewidth=0.5)
            ax.set_xlabel("Time (seconds)")
            ax.set_ylabel("Amplitude")
            ax.set_title("Audio Waveform")
            ax.grid(True, alpha=0.25)
            st.pyplot(fig)
            plt.close(fig)

            st.subheader("RMS Energy Over Time")
            if frame_rms:
                energy_times = (
                    np.arange(len(frame_rms)) * 0.05
                )
                fig, ax = plt.subplots(figsize=(12, 3))
                ax.plot(energy_times, frame_rms, linewidth=1)
                ax.set_xlabel("Time (seconds)")
                ax.set_ylabel("RMS Energy")
                ax.set_title("RMS Energy Graph")
                ax.grid(True, alpha=0.25)
                st.pyplot(fig)
                plt.close(fig)

            st.subheader("Low-Energy Regions")
            if frame_rms:
                threshold = max(
                    1e-6, float(np.max(np.abs(mono))) * 0.01
                )
                fig, ax = plt.subplots(figsize=(12, 3))
                ax.plot(energy_times, frame_rms, label="RMS energy")
                ax.axhline(
                    threshold, linestyle="--",
                    label="Low-energy threshold"
                )
                ax.set_xlabel("Time (seconds)")
                ax.set_ylabel("Energy")
                ax.set_title("Low-Energy Regions (50 ms frames)")
                ax.legend()
                ax.grid(True, alpha=0.25)
                st.pyplot(fig)
                plt.close(fig)

            st.warning(
                "Low energy or abrupt sample changes can occur naturally. "
                "They are not, by themselves, proof of an edit."
            )

            pdf = make_pdf(uploaded.name, digest, metrics)
            st.download_button(
                "📄 Download PDF Analysis Report",
                data=pdf,
                file_name="audio_forensic_report.pdf",
                mime="application/pdf"
            )

        except Exception as error:
            st.error(
                "The audio file could not be analysed. "
                "Please try a valid WAV, FLAC, or OGG file."
            )
            st.caption(f"Technical detail: {error}")

with tab2:
    st.write("Upload two audio files to compare their hashes and technical properties.")

    file_a = st.file_uploader(
        "First audio file",
        type=["wav", "flac", "ogg"],
        key="compare_a"
    )
    file_b = st.file_uploader(
        "Second audio file",
        type=["wav", "flac", "ogg"],
        key="compare_b"
    )

    if file_a is not None and file_b is not None:
        try:
            data_a, audio_a, rate_a = load_audio(file_a)
            data_b, audio_b, rate_b = load_audio(file_b)

            hash_a = sha256(data_a)
            hash_b = sha256(data_b)
            identical = hash_a == hash_b

            st.subheader("SHA-256 Comparison")
            col_a, col_b = st.columns(2)
            col_a.write(f"**{file_a.name}**")
            col_a.code(hash_a)
            col_b.write(f"**{file_b.name}**")
            col_b.code(hash_b)

            if identical:
                st.success("The files are byte-for-byte identical.")
            else:
                st.warning(
                    "The files differ at the byte level. "
                    "This alone does not establish tampering."
                )

            metrics_a, mono_a, rms_a = audio_metrics(audio_a, rate_a)
            metrics_b, mono_b, rms_b = audio_metrics(audio_b, rate_b)

            st.subheader("Technical Comparison")
            comparison_table = []
            for key in metrics_a:
                comparison_table.append({
                    "Metric": key,
                    file_a.name: metrics_a[key],
                    file_b.name: metrics_b[key]
                })
            st.dataframe(
                comparison_table,
                use_container_width=True,
                hide_index=True
            )

            st.subheader("Waveform Comparison")
            fig, axes = plt.subplots(2, 1, figsize=(12, 6))
            for ax, mono, rate, name in [
                (axes[0], mono_a, rate_a, file_a.name),
                (axes[1], mono_b, rate_b, file_b.name)
            ]:
                times = np.arange(len(mono)) / rate
                step = max(1, len(mono) // 100000)
                ax.plot(times[::step], mono[::step], linewidth=0.5)
                ax.set_title(name)
                ax.set_xlabel("Time (seconds)")
                ax.set_ylabel("Amplitude")
                ax.grid(True, alpha=0.25)
            fig.tight_layout()
            st.pyplot(fig)
            plt.close(fig)

            pdf = make_pdf(
                f"{file_a.name} vs {file_b.name}",
                hash_a,
                metrics_a,
                comparison=(
                    f"Second file: {file_b.name}. "
                    f"Second SHA-256: {hash_b}. "
                    f"Byte-for-byte identical: {identical}."
                )
            )
            st.download_button(
                "📄 Download Comparison Report",
                data=pdf,
                file_name="audio_comparison_report.pdf",
                mime="application/pdf"
            )

        except Exception as error:
            st.error("One or both files could not be analysed.")
            st.caption(f"Technical detail: {error}")

st.divider()
st.caption(
    "Academic project prototype • Digital Forensics of Audio • "
    "Use only audio files you are authorised to analyse."
)
