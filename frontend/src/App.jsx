import { useEffect, useMemo, useState } from "react";

import Plot from "react-plotly.js";

import {
  Waves,
  Send,
  Bot,
  MapPin,
  Database,
  Thermometer,
  Droplets,
  Activity,
  Compass,
  Layers3,
  Radio,
  Box,
} from "lucide-react";

import "./App.css";


const API_URL = "http://127.0.0.1:8001";


const starterQuestions = [
  "What is the average temperature around 78°E and 0°N?",
  "What is the salinity around 78°E and 0°N?",
  "What is the maximum temperature around 80°E and 5°N?",
];


function longitudeToX(longitude) {
  const minLongitude = 60;
  const maxLongitude = 100;

  return Math.max(
    0,
    Math.min(
      100,
      ((longitude - minLongitude) /
        (maxLongitude - minLongitude)) *
        100
    )
  );
}


function latitudeToY(latitude) {
  const minLatitude = -10;
  const maxLatitude = 20;

  return Math.max(
    0,
    Math.min(
      100,
      100 -
        ((latitude - minLatitude) /
          (maxLatitude - minLatitude)) *
          100
    )
  );
}


function formatCoordinate(value, positive, negative) {
  if (
    value === null ||
    value === undefined ||
    value === "—"
  ) {
    return "—";
  }

  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "—";
  }

  return `${Math.abs(number).toFixed(2)}°${
    number >= 0 ? positive : negative
  }`;
}


function capitalize(value) {
  if (!value) {
    return "";
  }

  return (
    value.charAt(0).toUpperCase() +
    value.slice(1)
  );
}


function App() {

  // ========================================================
  // DATASET
  // ========================================================

  const [dataset, setDataset] = useState(null);

  const [datasetLoading, setDatasetLoading] =
    useState(true);

  const [datasetError, setDatasetError] =
    useState(null);


  // ========================================================
  // FLOATS
  // ========================================================

  const [floats, setFloats] = useState([]);

  const [floatsLoading, setFloatsLoading] =
    useState(true);

  const [floatsError, setFloatsError] =
    useState(null);


  // ========================================================
  // VISUALIZATION
  // ========================================================

  const [visualization, setVisualization] =
    useState(null);

  const [
    visualizationLoading,
    setVisualizationLoading,
  ] = useState(true);

  const [
    visualizationError,
    setVisualizationError,
  ] = useState(null);


  // ========================================================
  // CHAT
  // ========================================================

  const [question, setQuestion] = useState("");

  const [loading, setLoading] =
    useState(false);

  const [messages, setMessages] = useState([
    {
      role: "bot",
      text:
        "Welcome to FLOATCHAT. I can explore the ARGO dataset and answer questions about ocean temperature, salinity, pressure and float observations.",
    },
  ]);


  // ========================================================
  // QUERY CONTEXT
  // ========================================================

  const [queryContext, setQueryContext] =
    useState({
      latitude: "—",
      longitude: "—",
      pressure: "—",
      variable: "—",
      statistic: "—",
    });


  // ========================================================
  // ANSWER
  // ========================================================

  const [answerData, setAnswerData] =
    useState({
      title: "WAITING FOR QUERY",
      value: "—",
      observations:
        "Ask a question to explore the dataset.",
    });


  // ========================================================
  // LOAD SUMMARY
  // ========================================================

  useEffect(() => {

    async function loadDataset() {

      try {

        setDatasetLoading(true);

        setDatasetError(null);

        const response =
          await fetch(
            `${API_URL}/summary`
          );

        if (!response.ok) {
          throw new Error(
            `Dataset API returned ${response.status}`
          );
        }

        const data =
          await response.json();

        setDataset(data);

      } catch (error) {

        console.error(
          "FLOATCHAT dataset error:",
          error
        );

        setDatasetError(
          error.message ||
            "Unable to connect to FLOATCHAT API"
        );

      } finally {

        setDatasetLoading(false);
      }
    }

    loadDataset();

  }, []);


  // ========================================================
  // LOAD FLOATS
  // ========================================================

  useEffect(() => {

    async function loadFloats() {

      try {

        setFloatsLoading(true);

        setFloatsError(null);

        const response =
          await fetch(
            `${API_URL}/floats`
          );

        if (!response.ok) {
          throw new Error(
            `Float API returned ${response.status}`
          );
        }

        const data =
          await response.json();

        if (!data.success) {
          throw new Error(
            data.error ||
              "Unable to load float locations"
          );
        }

        setFloats(
          Array.isArray(data.floats)
            ? data.floats
            : []
        );

      } catch (error) {

        console.error(
          "FLOATCHAT float error:",
          error
        );

        setFloatsError(
          error.message ||
            "Unable to load float locations"
        );

        setFloats([]);

      } finally {

        setFloatsLoading(false);
      }
    }

    loadFloats();

  }, []);


  // ========================================================
  // LOAD 3D VISUALIZATION
  // ========================================================

  useEffect(() => {

    async function loadVisualization() {

      try {

        setVisualizationLoading(true);

        setVisualizationError(null);

        const response =
          await fetch(
            `${API_URL}/visualization?max_points=6000`
          );

        if (!response.ok) {
          throw new Error(
            `Visualization API returned ${response.status}`
          );
        }

        const data =
          await response.json();

        if (!data.success) {
          throw new Error(
            data.error ||
              "Unable to load visualization data"
          );
        }

        setVisualization(data);

      } catch (error) {

        console.error(
          "FLOATCHAT visualization error:",
          error
        );

        setVisualizationError(
          error.message ||
            "Unable to load 3D visualization"
        );

      } finally {

        setVisualizationLoading(false);
      }
    }

    loadVisualization();

  }, []);


  // ========================================================
  // ASK QUESTION
  // ========================================================

  const askQuestion = async (
    customQuestion = null
  ) => {

    const currentQuestion =
      customQuestion ?? question;

    if (
      !currentQuestion.trim() ||
      loading
    ) {
      return;
    }

    setMessages(
      previous => [
        ...previous,
        {
          role: "user",
          text: currentQuestion,
        },
      ]
    );

    setQuestion("");

    setLoading(true);

    try {

      const response =
        await fetch(
          `${API_URL}/chat`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify({
              question:
                currentQuestion,
            }),
          }
        );

      if (!response.ok) {
        throw new Error(
          `Chat API returned ${response.status}`
        );
      }

      const result =
        await response.json();

      setMessages(
        previous => [
          ...previous,
          {
            role: "bot",
            text:
              result.answer ||
              "The dataset did not return a readable answer.",
          },
        ]
      );


      // ====================================================
      // UPDATE QUERY CONTEXT
      // ====================================================

      if (
        result.parameters &&
        Object.keys(
          result.parameters
        ).length > 0
      ) {

        const parameters =
          result.parameters;

        setQueryContext({

          latitude:
            formatCoordinate(
              parameters.latitude,
              "N",
              "S"
            ),

          longitude:
            formatCoordinate(
              parameters.longitude,
              "E",
              "W"
            ),

          pressure:
            parameters.min_pressure !==
              undefined &&
            parameters.max_pressure !==
              undefined
              ? `${parameters.min_pressure} – ${parameters.max_pressure} dbar`
              : "—",

          variable:
            parameters.variable
              ? capitalize(
                  parameters.variable
                )
              : "—",

          statistic:
            parameters.statistic
              ? capitalize(
                  parameters.statistic
                )
              : "—",
        });


        // ==================================================
        // ANSWER CARD
        // ==================================================

        const statistics =
          result.statistics || {};

        let title =
          "QUERY RESULT";

        let value =
          "—";

        if (
          parameters.variable ===
          "temperature"
        ) {

          title =
            `${capitalize(
              parameters.statistic ||
                "average"
            )} temperature`;

          if (
            parameters.statistic ===
              "minimum" &&
            statistics.minimum_temperature !==
              undefined
          ) {

            value =
              `${Number(
                statistics.minimum_temperature
              ).toFixed(2)}°C`;

          } else if (
            parameters.statistic ===
              "maximum" &&
            statistics.maximum_temperature !==
              undefined
          ) {

            value =
              `${Number(
                statistics.maximum_temperature
              ).toFixed(2)}°C`;

          } else if (
            statistics.mean_temperature !==
            undefined
          ) {

            value =
              `${Number(
                statistics.mean_temperature
              ).toFixed(2)}°C`;
          }

        } else if (
          parameters.variable ===
          "salinity"
        ) {

          title =
            `${capitalize(
              parameters.statistic ||
                "average"
            )} salinity`;

          if (
            parameters.statistic ===
              "minimum" &&
            statistics.minimum_salinity !==
              undefined
          ) {

            value =
              `${Number(
                statistics.minimum_salinity
              ).toFixed(2)} PSU`;

          } else if (
            parameters.statistic ===
              "maximum" &&
            statistics.maximum_salinity !==
              undefined
          ) {

            value =
              `${Number(
                statistics.maximum_salinity
              ).toFixed(2)} PSU`;

          } else if (
            statistics.mean_salinity !==
            undefined
          ) {

            value =
              `${Number(
                statistics.mean_salinity
              ).toFixed(2)} PSU`;
          }
        }

        setAnswerData({

          title:
            title.toUpperCase(),

          value,

          observations:
            statistics.count !==
            undefined
              ? `${Number(
                  statistics.count
                ).toLocaleString()} matching observations`
              : "Matching ARGO observations",
        });
      }

    } catch (error) {

      console.error(
        "FLOATCHAT chat error:",
        error
      );

      setMessages(
        previous => [
          ...previous,
          {
            role: "bot",
            text:
              "I couldn't reach the FLOATCHAT data service. Make sure FastAPI is running on port 8001.",
          },
        ]
      );

    } finally {

      setLoading(false);
    }
  };


  // ========================================================
  // SUBMIT
  // ========================================================

  const handleSubmit = event => {

    event.preventDefault();

    askQuestion();
  };


  // ========================================================
  // 3D PLOT DATA
  // ========================================================

  const plotData = useMemo(() => {

    if (
      !visualization ||
      !visualization.points
    ) {
      return [];
    }

    const points =
      visualization.points;

    return [

      {
        type: "scatter3d",

        mode: "markers",

        x: points.map(
          point =>
            point.longitude
        ),

        y: points.map(
          point =>
            point.latitude
        ),

        z: points.map(
          point =>
            point.pressure
        ),

        text: points.map(
          point =>
            `Float ${point.float_id}`
        ),

        customdata:
          points.map(
            point => [
              point.float_id,
              point.cycle_number,
              point.date,
              point.temperature,
              point.salinity,
            ]
          ),

        hovertemplate:
          "<b>ARGO Float %{customdata[0]}</b>" +
          "<br>Cycle: %{customdata[1]}" +
          "<br>Date: %{customdata[2]}" +
          "<br>Longitude: %{x:.2f}°" +
          "<br>Latitude: %{y:.2f}°" +
          "<br>Pressure: %{z:.1f} dbar" +
          "<br>Temperature: %{customdata[3]:.2f}°C" +
          "<br>Salinity: %{customdata[4]:.2f} PSU" +
          "<extra></extra>",

        marker: {

          size: 3,

          opacity: 0.72,

          color:
            points.map(
              point =>
                point.temperature
            ),

          colorscale:
            "Turbo",

          colorbar: {

            title: {
              text: "Temperature °C",
              side: "right",
            },

            thickness: 12,
          },

          showscale: true,
        },
      },

    ];

  }, [visualization]);


  // ========================================================
  // UI
  // ========================================================

  return (

    <div className="app-shell">

      <div className="background-glow glow-one" />

      <div className="background-glow glow-two" />


      {/* ====================================================
          SIDEBAR
      ==================================================== */}

      <aside className="navigation">

        <div className="logo-area">

          <div className="logo-mark">
            <Waves size={23} />
          </div>

          <div>

            <div className="logo-name">
              FLOATCHAT
            </div>

            <div className="logo-subtitle">
              Ocean data intelligence
            </div>

          </div>

        </div>


        <div className="navigation-group">

          <div className="navigation-heading">
            WORKSPACE
          </div>

          <div className="navigation-item selected">
            <Activity size={17} />
            <span>
              Ocean Assistant
            </span>
          </div>

          <div className="navigation-item">
            <Compass size={17} />
            <span>
              Float Explorer
            </span>
          </div>

          <div className="navigation-item">
            <Layers3 size={17} />
            <span>
              Profile Data
            </span>
          </div>

        </div>


        <div className="navigation-bottom">

          <div className="connection-card">

            <div className="connection-icon">
              <Radio size={15} />
            </div>

            <div>

              <div className="connection-title">

                {datasetLoading
                  ? "Connecting..."
                  : datasetError
                    ? "Connection failed"
                    : "Dataset connected"}

              </div>

              <div className="connection-description">

                {dataset
                  ? `${Number(
                      dataset.rows
                    ).toLocaleString()} observations`
                  : datasetError
                    ? "Check FastAPI"
                    : "ARGO dataset"}

              </div>

            </div>

            <span
              className={
                datasetError
                  ? "pulse pulse-error"
                  : "pulse"
              }
            />

          </div>

        </div>

      </aside>


      {/* ====================================================
          MAIN
      ==================================================== */}

      <main className="workspace">


        {/* ==================================================
            HEADER
        ================================================== */}

        <header className="topbar">

          <div>

            <div className="section-kicker">
              ARGO OCEAN OBSERVATION SYSTEM
            </div>

            <h1>
              Ask the ocean.
              <span>
                {" "}Get the data.
              </span>
            </h1>

            <p className="intro">
              Explore measurements collected by
              autonomous ARGO floats using
              natural language.
            </p>

          </div>


          <div className="dataset-badge">

            <span
              className={
                datasetError
                  ? "pulse pulse-error"
                  : "pulse"
              }
            />

            <div>

              <strong>

                {datasetLoading
                  ? "Connecting..."
                  : datasetError
                    ? "Connection failed"
                    : "Dataset online"}

              </strong>

              <small>

                {dataset
                  ? `${Number(
                      dataset.rows
                    ).toLocaleString()} measurements`
                  : datasetError
                    ? "FastAPI :8001"
                    : "Loading dataset..."}

              </small>

            </div>

          </div>

        </header>


        {/* ==================================================
            SNAPSHOT
        ================================================== */}

        <DatasetSnapshot
          dataset={dataset}
          loading={datasetLoading}
          error={datasetError}
        />


        {/* ==================================================
            CHAT + MAP
        ================================================== */}

        <section className="primary-grid">


          {/* =================================================
              CHAT
          ================================================= */}

          <section className="chat-card">

            <div className="card-heading">

              <div className="assistant-heading">

                <div className="assistant-symbol">
                  <Bot size={18} />
                </div>

                <div>

                  <h2>
                    FLOATCHAT
                  </h2>

                  <span>
                    Natural-language ocean query
                  </span>

                </div>

              </div>


              <div className="assistant-status">

                <span className="pulse" />

                {loading
                  ? "Searching"
                  : "Ready"}

              </div>

            </div>


            <div className="conversation">

              {messages.map(
                (message, index) => (

                  <div
                    className={`message-row ${message.role}`}
                    key={index}
                  >

                    {message.role ===
                      "bot" && (

                      <div className="message-icon">
                        <Bot size={13} />
                      </div>

                    )}

                    <div className="message-text">
                      {message.text}
                    </div>

                  </div>

                )
              )}


              {loading && (

                <div className="message-row bot">

                  <div className="message-icon">
                    <Bot size={13} />
                  </div>

                  <div className="message-text thinking">
                    Reading ARGO measurements...
                  </div>

                </div>

              )}

            </div>


            <div className="suggestion-area">

              <span>
                Try asking
              </span>

              <div className="suggestion-buttons">

                {starterQuestions
                  .slice(0, 2)
                  .map(item => (

                    <button
                      key={item}
                      type="button"
                      onClick={() =>
                        askQuestion(item)
                      }
                    >

                      {item.length > 45
                        ? `${item.substring(
                            0,
                            45
                          )}...`
                        : item}

                    </button>

                  ))}

              </div>

            </div>


            <form
              className="question-box"
              onSubmit={handleSubmit}
            >

              <input

                value={question}

                onChange={event =>
                  setQuestion(
                    event.target.value
                  )
                }

                placeholder="Ask about temperature, salinity, pressure or location..."

              />

              <button
                type="submit"
                disabled={
                  loading ||
                  !question.trim()
                }
              >
                <Send size={16} />
              </button>

            </form>

          </section>


          {/* =================================================
              FLOAT MAP
          ================================================= */}

          <section className="map-card">

            <div className="card-heading">

              <div>

                <h2>
                  Float field
                </h2>

                <span>
                  Indian Ocean observation region
                </span>

              </div>

              <MapPin size={17} />

            </div>


            <div className="ocean-field">

              <div className="longitude longitude-one" />
              <div className="longitude longitude-two" />
              <div className="longitude longitude-three" />

              <div className="latitude latitude-one" />
              <div className="latitude latitude-two" />
              <div className="latitude latitude-three" />


              <div className="land-shape land-india" />
              <div className="land-shape land-sri" />


              <div className="region-label">
                INDIAN OCEAN
              </div>


              {floats.map(float => (

                <span
                  key={float.float_id}
                  className="float-point"
                  title={`ARGO Float ${float.float_id}`}
                  style={{
                    left: `${longitudeToX(
                      float.longitude
                    )}%`,

                    top: `${latitudeToY(
                      float.latitude
                    )}%`,
                  }}
                />

              ))}


              <div className="float-count">

                {floatsLoading
                  ? "Loading ARGO floats..."
                  : floatsError
                    ? "Float data unavailable"
                    : `${floats.length} ARGO floats`}

              </div>


              <div className="map-scale">

                <span>60°E</span>

                <span>80°E</span>

                <span>100°E</span>

              </div>

            </div>

          </section>

        </section>


        {/* ==================================================
            3D VISUALIZATION
        ================================================== */}

        <section className="ocean-3d-card">

          <div className="card-heading">

            <div className="visualization-title-row">

              <div className="visualization-icon">
                <Box size={17} />
              </div>

              <div>

                <h2>
                  3D ocean observation field
                </h2>

                <span>
                  Temperature distribution across longitude,
                  latitude and pressure
                </span>

              </div>

            </div>


            <div className="visualization-badge">

              {visualizationLoading
                ? "LOADING"
                : visualizationError
                  ? "UNAVAILABLE"
                  : `${Number(
                      visualization?.count || 0
                    ).toLocaleString()} POINTS`}

            </div>

          </div>


          <div className="visualization-description">

            Each point represents an ARGO observation.
            Vertical position represents pressure in dbar,
            while colour represents measured temperature.

          </div>


          <div className="ocean-3d-container">

            {visualizationLoading && (

              <div className="visualization-state">

                <div className="spinner" />

                <strong>
                  Loading ocean observations
                </strong>

                <span>
                  Preparing the 3D observation field...
                </span>

              </div>

            )}


            {!visualizationLoading &&
              visualizationError && (

                <div className="visualization-state error">

                  <strong>
                    Visualization unavailable
                  </strong>

                  <span>
                    {visualizationError}
                  </span>

                </div>

              )}


            {!visualizationLoading &&
              !visualizationError &&
              visualization &&
              visualization.points?.length > 0 && (

                <Plot

                  data={plotData}

                  layout={{

                    autosize: true,

                    margin: {
                      l: 0,
                      r: 0,
                      b: 0,
                      t: 5,
                    },

                    paper_bgcolor:
                      "rgba(0,0,0,0)",

                    plot_bgcolor:
                      "rgba(0,0,0,0)",

                    scene: {

                      bgcolor:
                        "rgba(0,0,0,0)",

                      xaxis: {
                        title:
                          "Longitude",
                        gridcolor:
                          "#dbeaf2",
                        zerolinecolor:
                          "#dbeaf2",
                      },

                      yaxis: {
                        title:
                          "Latitude",
                        gridcolor:
                          "#dbeaf2",
                        zerolinecolor:
                          "#dbeaf2",
                      },

                      zaxis: {
                        title:
                          "Pressure (dbar)",
                        autorange:
                          "reversed",
                        gridcolor:
                          "#dbeaf2",
                        zerolinecolor:
                          "#dbeaf2",
                      },

                      camera: {
                        eye: {
                          x: 1.45,
                          y: 1.35,
                          z: 1.05,
                        },
                      },
                    },

                    showlegend: false,

                  }}

                  config={{
                    responsive: true,
                    displaylogo: false,
                    modeBarButtonsToRemove: [
                      "lasso3d",
                      "select3d",
                    ],
                  }}

                  style={{
                    width: "100%",
                    height: "100%",
                  }}

                  useResizeHandler

                />

              )}


          </div>


          {!visualizationLoading &&
            !visualizationError &&
            visualization && (

              <div className="visualization-footer">

                <span>
                  {Number(
                    visualization.total_available || 0
                  ).toLocaleString()}{" "}
                  valid observations available
                </span>

                <span>
                  •
                </span>

                <span>
                  Showing{" "}
                  {Number(
                    visualization.count || 0
                  ).toLocaleString()}{" "}
                  sampled points
                </span>

              </div>

            )}

        </section>


        {/* ==================================================
            LOWER GRID
        ================================================== */}

        <section className="secondary-grid">


          {/* =================================================
              QUERY CONTEXT
          ================================================= */}

          <section className="context-card">

            <div className="card-heading">

              <div>

                <h2>
                  Query context
                </h2>

                <span>
                  Detected from your request
                </span>

              </div>

              <Compass size={17} />

            </div>


            <div className="context-list">

              <ContextRow
                label="Latitude"
                value={
                  queryContext.latitude
                }
              />

              <ContextRow
                label="Longitude"
                value={
                  queryContext.longitude
                }
              />

              <ContextRow
                label="Pressure range"
                value={
                  queryContext.pressure
                }
              />

              <ContextRow
                label="Variable"
                value={
                  queryContext.variable
                }
              />

              <ContextRow
                label="Statistic"
                value={
                  queryContext.statistic
                }
              />

            </div>


            <div className="answer-highlight">

              <span>
                {answerData.title}
              </span>

              <strong>
                {answerData.value}
              </strong>

              <small>
                {answerData.observations}
              </small>

            </div>

          </section>


          {/* =================================================
              DATASET INFORMATION
          ================================================= */}

          <section className="profile-card">

            <div className="card-heading">

              <div>

                <h2>
                  Dataset coverage
                </h2>

                <span>
                  Current ARGO data extent
                </span>

              </div>

              <Database size={17} />

            </div>


            <div className="coverage-grid">

              <CoverageItem
                label="Latitude"
                value={
                  dataset
                    ? `${Number(
                        dataset.latitude_min
                      ).toFixed(1)}° to ${Number(
                        dataset.latitude_max
                      ).toFixed(1)}°`
                    : "—"
                }
              />

              <CoverageItem
                label="Longitude"
                value={
                  dataset
                    ? `${Number(
                        dataset.longitude_min
                      ).toFixed(1)}° to ${Number(
                        dataset.longitude_max
                      ).toFixed(1)}°`
                    : "—"
                }
              />

              <CoverageItem
                label="Pressure"
                value={
                  dataset
                    ? `${Number(
                        dataset.pressure_min
                      ).toFixed(0)} – ${Number(
                        dataset.pressure_max
                      ).toFixed(0)} dbar`
                    : "—"
                }
              />

              <CoverageItem
                label="Floats"
                value={
                  dataset
                    ? Number(
                        dataset.floats
                      ).toLocaleString()
                    : "—"
                }
              />

            </div>

          </section>

        </section>


        <footer className="footer">
          FLOATCHAT · ARGO ocean observation interface
        </footer>

      </main>

    </div>
  );
}


// ============================================================
// DATASET SNAPSHOT
// ============================================================

function DatasetSnapshot({
  dataset,
  loading,
  error,
}) {

  return (

    <section className="snapshot">

      <SnapshotCard
        icon={<Database size={18} />}
        label="Measurements"
        value={
          dataset
            ? Number(
                dataset.rows
              ).toLocaleString()
            : error
              ? "Unavailable"
              : loading
                ? "Loading..."
                : "—"
        }
      />

      <SnapshotCard
        icon={<MapPin size={18} />}
        label="ARGO floats"
        value={
          dataset
            ? Number(
                dataset.floats
              ).toLocaleString()
            : error
              ? "Unavailable"
              : loading
                ? "Loading..."
                : "—"
        }
      />

      <SnapshotCard
        icon={<Thermometer size={18} />}
        label="Temperature"
        value={
          dataset
            ? `${Number(
                dataset.temperature_min
              ).toFixed(1)} — ${Number(
                dataset.temperature_max
              ).toFixed(1)}°C`
            : error
              ? "Unavailable"
              : loading
                ? "Loading..."
                : "—"
        }
      />

      <SnapshotCard
        icon={<Droplets size={18} />}
        label="Salinity"
        value={
          dataset
            ? `${Number(
                dataset.salinity_min
              ).toFixed(1)} — ${Number(
                dataset.salinity_max
              ).toFixed(1)} PSU`
            : error
              ? "Unavailable"
              : loading
                ? "Loading..."
                : "—"
        }
      />

    </section>
  );
}


// ============================================================
// SNAPSHOT CARD
// ============================================================

function SnapshotCard({
  icon,
  label,
  value,
}) {

  return (

    <div className="snapshot-card">

      <div className="snapshot-icon">
        {icon}
      </div>

      <div className="snapshot-text">

        <span>
          {label}
        </span>

        <strong>
          {value}
        </strong>

      </div>

    </div>
  );
}


// ============================================================
// CONTEXT ROW
// ============================================================

function ContextRow({
  label,
  value,
}) {

  return (

    <div className="context-row">

      <span>
        {label}
      </span>

      <strong>
        {value}
      </strong>

    </div>
  );
}


// ============================================================
// COVERAGE ITEM
// ============================================================

function CoverageItem({
  label,
  value,
}) {

  return (

    <div className="coverage-item">

      <span>
        {label}
      </span>

      <strong>
        {value}
      </strong>

    </div>
  );
}


export default App;