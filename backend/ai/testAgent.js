const { extractRequirements } = require("./queryAgent");

async function test() {
  const prompt =
    "I'm a 3rd year AI & DS student looking for a paid AI internship in Chennai or remote. I know Python and TensorFlow.";

  try {
    const result = await extractRequirements(prompt);

    console.log("AI OUTPUT:");
    console.log(JSON.stringify(result, null, 2));
  } catch (error) {
    console.error("ERROR:", error.message);
  }
}

test();