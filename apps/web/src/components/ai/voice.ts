"use client";

import * as React from "react";

type Recognition = {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  start: () => void;
  stop: () => void;
  onresult: ((e: { results: ArrayLike<ArrayLike<{ transcript: string }> & { isFinal: boolean }> }) => void) | null;
  onend: (() => void) | null;
  onerror: ((e: { error: string }) => void) | null;
};

function getRecognition(): Recognition | null {
  if (typeof window === "undefined") return null;
  const W = window as unknown as { SpeechRecognition?: new () => Recognition; webkitSpeechRecognition?: new () => Recognition };
  const Ctor = W.SpeechRecognition ?? W.webkitSpeechRecognition;
  return Ctor ? new Ctor() : null;
}

/** Browser speech-to-text with a live microphone level for the orb and waveform. */
export function useVoice(onFinal: (text: string) => void) {
  const [listening, setListening] = React.useState(false);
  const [interim, setInterim] = React.useState("");
  const [level, setLevel] = React.useState(0);
  const [error, setError] = React.useState<string | null>(null);
  const recRef = React.useRef<Recognition | null>(null);
  const streamRef = React.useRef<MediaStream | null>(null);
  const rafRef = React.useRef<number>(0);
  const supported = typeof window !== "undefined" && !!getRecognition();

  const cleanupAudio = React.useCallback(() => {
    cancelAnimationFrame(rafRef.current);
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setLevel(0);
  }, []);

  const stop = React.useCallback(() => {
    recRef.current?.stop();
    setListening(false);
    cleanupAudio();
  }, [cleanupAudio]);

  const start = React.useCallback(async () => {
    setError(null);
    const rec = getRecognition();
    if (!rec) {
      setError("Voice input isn't supported in this browser. Try Chrome or Edge.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const ctx = new AudioContext();
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      ctx.createMediaStreamSource(stream).connect(analyser);
      const data = new Uint8Array(analyser.frequencyBinCount);
      const tick = () => {
        analyser.getByteFrequencyData(data);
        const avg = data.reduce((a, b) => a + b, 0) / data.length;
        setLevel(Math.min(1, avg / 90));
        rafRef.current = requestAnimationFrame(tick);
      };
      tick();
    } catch {
      setError("Microphone access was blocked. You can still type your question.");
      return;
    }
    rec.lang = "en-US";
    rec.interimResults = true;
    rec.continuous = false;
    rec.onresult = (e) => {
      let text = "";
      let final = false;
      for (let i = 0; i < e.results.length; i++) {
        text += e.results[i][0].transcript;
        if (e.results[i].isFinal) final = true;
      }
      setInterim(text);
      if (final) {
        onFinal(text);
        setInterim("");
      }
    };
    rec.onerror = (e) => {
      if (e.error !== "no-speech" && e.error !== "aborted") setError("I couldn't hear that clearly. Please try again.");
    };
    rec.onend = () => {
      setListening(false);
      cleanupAudio();
    };
    recRef.current = rec;
    rec.start();
    setListening(true);
  }, [onFinal, cleanupAudio]);

  React.useEffect(() => () => stop(), [stop]);

  return { supported, listening, interim, level, error, start, stop };
}

/** Speaks a short, markdown-stripped version of an answer. */
export function speak(text: string) {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
  const plain = text.replace(/\[\d+\]/g, "").replace(/[*_>#`]/g, "").replace(/\n+/g, " ").slice(0, 420);
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(plain);
  u.rate = 1.02;
  window.speechSynthesis.speak(u);
}
