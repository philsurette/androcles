class LineRecorderWorklet extends AudioWorkletProcessor {
  process(inputs) {
    const input = inputs[0];
    if (!input || input.length === 0) {
      return true;
    }
    const channel = input[0];
    if (!channel || channel.length === 0) {
      return true;
    }
    const samples = new Float32Array(channel);
    this.port.postMessage(samples, [samples.buffer]);
    return true;
  }
}

registerProcessor("line-recorder-worklet", LineRecorderWorklet);
