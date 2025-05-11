const featureEmojis = {
  "Total Precipitation": "🌧️", "Surface Pressure": "📈", "2m Specific Humidity": "💧",
  "2m Temperature": "🌡️", "2m Dew Point Temperature": "🌫️", "2m Wet Bulb Temperature": "💦",
  "2m Maximum Temperature": "🔥", "2m Minimum Temperature": "❄️", "2m Temperature Range": "📊",
  "Surface Temperature": "🌍", "10m Wind Speed": "🌬️", "10m Maximum Wind Speed": "🌬️",
  "10m Minimum Wind Speed": "🌬️", "10m Wind Speed Range": "📏", "50m Wind Speed": "🌀",
  "50m Maximum Wind Speed": "🌀", "50m Minimum Wind Speed": "🌀", "50m Wind Speed Range": "📏",
  "Temperature (°C)": "🌡️", "Humidity (%)": "💧", "Precipitation (mm)": "🌧️",
  "Soil Moisture (%)": "🌱", "Elevation (m)": "⛰️", elevation: "⛰️", temperature: "🌡️",
  wind_speed: "🌬️", humidity: "💧", snow_depth: "❄️"
};

function buildFieldsUI(fields) {
  let html = "";
  fields.forEach(field => {
    const emoji = featureEmojis[field.display_name] || featureEmojis[field.feature_name] || "🔧";
    const initVal = (field.min_val + field.max_val) / 2;
    html += `
      <div class="col-12 col-md-6 field-block mb-3">
        <label class="form-label">
          <span class="emoji-colored">${emoji}</span>
          ${field.display_name}
          <small class="text-muted">(Range: ${field.min_val} – ${field.max_val})</small>
        </label>
        <input type="number"
               class="form-control form-input"
               data-feature="${field.feature_name}"
               data-min="${field.min_val}"
               data-max="${field.max_val}"
               value="${initVal}" />
      </div>
    `;
  });
  $("#field-container").html(html);
}

function showRiskTips(riskLevel, disasterType) {
  let tipMessage = "";

  // Determine the appropriate risk tip based on disaster type and risk level
  if (disasterType === "Drought") {
    if (riskLevel === "Extreme") {
      tipMessage = "🌟 Extreme drought ahead! Stay hydrated and minimize water usage.";
    } else if (riskLevel === "High") {
      tipMessage = "🌟 High drought risk! Water conservation is crucial.";
    } else if (riskLevel === "Medium") {
      tipMessage = "🌟 Moderate drought risk! Monitor water usage.";
    } else {
      tipMessage = "🌟 Stay alert! Drought is not imminent, but always be prepared.";
    }
  } else if (disasterType === "Avalanche") {
    if (riskLevel === "High") {
      tipMessage = "⛷️ Avalanche risk high? Avoid high-altitude snowy areas.";
    } else if (riskLevel === "Medium") {
      tipMessage = "⛷️ Moderate avalanche risk. Be cautious in the mountains.";
    } else {
      tipMessage = "⛷️ Low avalanche risk. However, remain vigilant in snowy regions.";
    }
  } else if (disasterType === "Landslide") {
    if (riskLevel === "High") {
      tipMessage = "⚠️ High landslide risk! Avoid steep slopes and monitor rainfall.";
    } else if (riskLevel === "Medium") {
      tipMessage = "⚠️ Moderate landslide risk. Stay alert during rainy periods.";
    } else {
      tipMessage = "⚠️ Low landslide risk. But always monitor the weather conditions.";
    }
  }

  // Display the tip message below the result box
  $("#tips-box").html(tipMessage).show();
}

function updateMap(predictions) {
  const lats = predictions.map(p => p.lat);
  const lons = predictions.map(p => p.lon);
  const texts = predictions.map(p => `${p.city} - ${p.disaster_type} (${p.risk_level})`);
  const colors = predictions.map(p => {
    if (["Extreme", "High"].includes(p.risk_level)) return "red";
    if (p.risk_level === "Medium") return "orange";
    return "green";
  });

  Plotly.newPlot("map-chart", [{
    type: "scattergeo",
    mode: "markers",
    lat: lats,
    lon: lons,
    text: texts,
    marker: { size: 10, color: colors, line: { width: 1, color: "#000" } }
  }], {
    geo: {
      projection: { type: "natural earth" },
      showland: true,
      landcolor: "#e5e5e5",
      oceancolor: "#cce6ff",
      showocean: true,
      countrycolor: "#888",
      showcountries: true,
      showframe: false,
      showcoastlines: true,
    },
    margin: { t: 0, b: 0, l: 0, r: 0 },
    width: document.getElementById("map-chart").offsetWidth,
    height: 500
  }, { responsive: true });
}

function updateTable(predictions) {
  const rows = predictions.map(p => `
    <tr>
      <td>${p.prediction_time}</td>
      <td>${p.city || ""}</td>
      <td>${p.disaster_type}</td>
      <td>${p.risk_level}</td>
    </tr>`).join('');
  $("#predictions-table-body").html(rows);
}

function loadPredictions() {
  $.get("/get-predictions/", res => {
    if (res.predictions) {
      updateMap(res.predictions);
      updateTable(res.predictions);
    }
  });
}

$(document).ready(() => {
  loadPredictions();

  $("#disaster-select").on("change", function () {
    const type = $(this).val();
    if (!type) return;
    $.get("/get-fields/", { disaster_type: type }, res => {
      buildFieldsUI(res.fields);
      $("#predict-btn").show();
    });
  });

  $(document).on("input", ".form-input", function () {
    const val = parseFloat($(this).val());
    const min = parseFloat($(this).data("min"));
    const max = parseFloat($(this).data("max"));
    $(this).toggleClass("out-of-range", val < min || val > max);
  });

  $("#fetch-weather-btn").on("click", function () {
    const city = $("#city-input").val().trim();
    if (!city) return alert("Enter a city!");
    $.get("/fetch-weather/", { city }, res => {
      if (res.error) return alert(res.error);
      $("#w-temp").text(res.temperature ?? "--");
      $("#w-humidity").text(res.humidity ?? "--");
      $("#w-pressure").text(res.pressure ?? "--");
      $("#w-wind").text(res.wind_speed ?? "--");
      $("#w-dir").text("↙");

      window.globalLat = res.lat;
      window.globalLon = res.lon;

      const type = $("#disaster-select").val();
      if (type === "Drought") {
        $(`[data-feature="T2M"]`).val(res.temperature).trigger("input");
        $(`[data-feature="QV2M"]`).val(res.humidity / 100).trigger("input");
        $(`[data-feature="PS"]`).val(res.pressure).trigger("input");
        $(`[data-feature="WS10M"]`).val(res.wind_speed).trigger("input");
      } else if (type === "Landslide") {
        $(`[data-feature="Temperature (°C)"]`).val(res.temperature).trigger("input");
        $(`[data-feature="Humidity (%)"]`).val(res.humidity).trigger("input");
      } else if (type === "Avalanche") {
        $(`[data-feature="temperature"]`).val(res.temperature).trigger("input");
        $(`[data-feature="humidity"]`).val(res.humidity).trigger("input");
        $(`[data-feature="wind_speed"]`).val(res.wind_speed).trigger("input");
      }
    });
  });

  $("#predict-btn").on("click", function () {
    const disaster = $("#disaster-select").val();
    const city = $("#city-input").val().trim();
    const formValues = {};
    $(".form-input").each(function () {
      formValues[$(this).data("feature")] = $(this).val();
    });

    $.ajax({
      url: "/ajax-predict/",
      method: "POST",
      contentType: "application/json",
      data: JSON.stringify({
        disaster_type: disaster,
        form_values: formValues,
        city: city,
        latitude: window.globalLat || null,
        longitude: window.globalLon || null
      }),
      success: function (res) {
        $("#warning-box, #result-box").hide().empty();
        if (res.warnings?.length) {
          $("#warning-box").html("<ul>" + res.warnings.map(w => `<li>${w}</li>`).join('') + "</ul>").show();
        }
        if (res.result) {
          $("#result-box").text(`Predicted ${disaster} Risk Level: ${res.result}`).show();
          showRiskTips(res.result, disaster);  // Show risk tip based on prediction
          loadPredictions();
        }
      }
    });
  });
});
