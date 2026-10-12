// Replaceable browser adapter. No raw audio is saved by this application.
export interface SpeechAdapter {
  available: boolean;
  start: (
    result: (text: string) => void,
    error: (message: string) => void,
  ) => void;
  stop: () => void;
  speak: (text: string) => void;
  cancel: () => void;
}
export function browserSpeech(): SpeechAdapter {
  const browser = window as unknown as {
    SpeechRecognition?: new () => any;
    webkitSpeechRecognition?: new () => any;
  };
  const Recognition =
    browser.SpeechRecognition || browser.webkitSpeechRecognition;
  let recognition: any;
  return {
    available: Boolean(Recognition),
    start(result, error) {
      if (!Recognition) {
        error("Speech input is unavailable. Continue by typing.");
        return;
      }
      recognition = new Recognition();
      recognition.lang = "en-US";
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.onresult = (event: any) =>
        result(event.results[0][0].transcript);
      recognition.onerror = () =>
        error(
          "Speech stopped or failed. Your draft is preserved; continue by typing.",
        );
      recognition.onend = () =>
        error("Listening stopped. Review your draft before confirmation.");
      try {
        recognition.start();
      } catch {
        error("Speech could not start. Continue by typing.");
      }
    },
    stop() {
      recognition?.stop();
    },
    speak(text) {
      if ("speechSynthesis" in window) {
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(new SpeechSynthesisUtterance(text));
      }
    },
    cancel() {
      recognition?.abort();
      if ("speechSynthesis" in window) window.speechSynthesis.cancel();
    },
  };
}
