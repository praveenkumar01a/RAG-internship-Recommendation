const express = require("express");
const cors = require("cors");
const fs = require("fs");
const path = require("path");

const app = express();
const PORT = 5000;

app.use(cors());
app.use(express.json());

// Load internship data
const dataPath = path.join(__dirname, "../data/internships.json");
const internships = JSON.parse(fs.readFileSync(dataPath, "utf-8"));

// Test API
app.get("/", (req, res) => {
  res.json({
    message: "AI Internship Discovery API is running"
  });
});

// Get all internships
app.get("/api/internships", (req, res) => {
  res.json(internships);
});

// Search internships using basic filters
app.get("/api/internships/search", (req, res) => {
  const {
    location,
    domain,
    work_mode,
    min_stipend
  } = req.query;

  let results = internships;

  if (location) {
    results = results.filter((internship) =>
      internship.location
        ?.toLowerCase()
        .includes(location.toLowerCase())
    );
  }

  if (domain) {
    results = results.filter((internship) =>
      internship.domain?.some((d) =>
        d.toLowerCase().includes(domain.toLowerCase())
      )
    );
  }

  if (work_mode) {
    results = results.filter(
      (internship) =>
        internship.work_mode?.toLowerCase() ===
        work_mode.toLowerCase()
    );
  }

  if (min_stipend) {
    results = results.filter(
      (internship) =>
        Number(internship.stipend) >= Number(min_stipend)
    );
  }

  res.json({
    count: results.length,
    results
  });
});

app.listen(PORT, () => {
  console.log(`Server running at http://localhost:${PORT}`);
});