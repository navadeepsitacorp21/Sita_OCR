/**
 * Formats a raw report date string (e.g. "07/11/2021", "2025-10-08", "08-Oct-2025")
 * into a clean medical display string like "07 Nov 2021".
 * Returns null if input is missing or unparseable.
 */
export function formatReportDate(dateStr) {
  if (!dateStr || typeof dateStr !== "string") return null;

  const trimmed = dateStr.trim();
  if (!trimmed) return null;

  const cleaned = trimmed
    .replace(/([A-Za-z]{3,9}[,\s\/\-\.]*)202[Xx]\b/gi, "$12022")
    .replace(/([A-Za-z]{3,9}[,\s\/\-\.]*)2[Xx]\b/gi, "$122");

  // Month name first: e.g. "Nov 07, 2021" or "Nov 7 2021"
  const monFirstMatch = cleaned.match(/^([A-Za-z]{3,9})\s+(\d{1,2})(?:st|nd|rd|th)?,?\s*(\d{2,4})/);
  if (monFirstMatch) {
    const monStr = monFirstMatch[1].toLowerCase().slice(0, 3);
    const day = parseInt(monFirstMatch[2], 10);
    let year = parseInt(monFirstMatch[3], 10);
    if (year < 100) year += 2000;

    const months = {
      jan: 0, feb: 1, mar: 2, apr: 3, may: 4, jun: 5,
      jul: 6, aug: 7, sep: 8, oct: 9, nov: 10, dec: 11
    };
    if (monStr in months) {
      const d = new Date(year, months[monStr], day);
      if (!isNaN(d.getTime()) && d.getDate() === day && d.getMonth() === months[monStr]) {
        return d.toLocaleDateString("en-GB", {
          day: "2-digit",
          month: "short",
          year: "numeric",
        });
      }
    }
  }

  // DD/MM/YYYY or DD-MM-YYYY
  const dmyMatch = cleaned.match(/^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})/);
  if (dmyMatch) {
    const day = parseInt(dmyMatch[1], 10);
    const month = parseInt(dmyMatch[2], 10) - 1;
    let year = parseInt(dmyMatch[3], 10);
    if (year < 100) year += 2000;

    const d = new Date(year, month, day);
    if (!isNaN(d.getTime()) && d.getDate() === day && d.getMonth() === month) {
      return d.toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      });
    }
  }

  // ISO YYYY-MM-DD
  const isoMatch = cleaned.match(/^(\d{4})[-/](\d{1,2})[-/](\d{1,2})/);
  if (isoMatch) {
    const year = parseInt(isoMatch[1], 10);
    const month = parseInt(isoMatch[2], 10) - 1;
    const day = parseInt(isoMatch[3], 10);

    const d = new Date(year, month, day);
    if (!isNaN(d.getTime()) && d.getDate() === day && d.getMonth() === month) {
      return d.toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      });
    }
  }

  // DD-Mon-YYYY or DD Mon, YYYY or DDMonYYYY
  const monMatch = cleaned.match(/^(\d{1,2})[/\-.\s,]*([A-Za-z]{3,9})[/\-.\s,]*(\d{2,4})/);
  if (monMatch) {
    const day = parseInt(monMatch[1], 10);
    const monStr = monMatch[2].toLowerCase().slice(0, 3);
    let year = parseInt(monMatch[3], 10);
    if (year < 100) year += 2000;

    const months = {
      jan: 0, feb: 1, mar: 2, apr: 3, may: 4, jun: 5,
      jul: 6, aug: 7, sep: 8, oct: 9, nov: 10, dec: 11
    };
    if (monStr in months) {
      const d = new Date(year, months[monStr], day);
      if (!isNaN(d.getTime()) && d.getDate() === day && d.getMonth() === months[monStr]) {
        return d.toLocaleDateString("en-GB", {
          day: "2-digit",
          month: "short",
          year: "numeric",
        });
      }
    }
  }

  return null;
}

/**
 * Formats an ISO-8601 timestamp or Date object into user's local time:
 * "27 Oct 2026 · 06:42 PM".
 * Returns null if input is missing or unparseable.
 */
export function formatDateTime(dateVal) {
  if (!dateVal) return null;
  let str = String(dateVal).trim();
  if (!str || str.toLowerCase() === "null" || str.toLowerCase() === "undefined") return null;

  // If timestamp string lacks timezone designator (no 'Z' and no offset like '+00:00'),
  // treat as UTC so browser converts accurately to user's local display timezone
  if (str.includes(" ") && !str.includes("T")) {
    str = str.replace(" ", "T");
  }
  if (!str.endsWith("Z") && !/[+-]\d{2}:\d{2}$/.test(str)) {
    str += "Z";
  }

  const d = new Date(str);
  if (isNaN(d.getTime())) return null;

  const datePart = d.toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });

  const timePart = d.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });

  return `${datePart} · ${timePart}`;
}

/**
 * Formats system analyzed/uploaded timestamp into human readable format like "27 Oct 2026 · 06:42 PM"
 */
export function formatAnalyzedDate(dateVal) {
  const formatted = formatDateTime(dateVal);
  if (formatted) return formatted;
  if (!dateVal) return "Unavailable";
  return String(dateVal);
}

