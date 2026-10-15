const extractionPrompt = require("./prompt");

async function extractRequirements(studentPrompt) {
  const response = await fetch("http://localhost:11434/api/generate", {
    method: "POST",

    headers: {
      "Content-Type": "application/json"
    },

    body: JSON.stringify({
      model: process.env.LLM_MODEL || "qwen2.5:1.5b",

      prompt: extractionPrompt + "\n" + studentPrompt,

      stream: false,

      format: "json",

      // Disable Qwen's thinking mode
      think: false
    })
  });

  if (!response.ok) {
    throw new Error(`Ollama error: ${response.status}`);
  }

  const data = await response.json();

  console.log("\n===== OLLAMA RESPONSE =====");
  console.log(JSON.stringify(data, null, 2));
  console.log("===== END RESPONSE =====\n");

  // Qwen should normally put the JSON here
  const output = data.response;

  if (!output || output.trim() === "") {
    throw new Error("Qwen returned an empty response.");
  }

  return JSON.parse(output);
}

module.exports = {
  extractRequirements
};