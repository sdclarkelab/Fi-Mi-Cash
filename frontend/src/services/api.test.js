// Mock axios before importing api
jest.mock("axios", () => {
  return {
    __esModule: true,
    default: {
      create: jest.fn(() => ({
        defaults: {
          headers: {
            "Content-Type": "application/json",
            "X-API-Key": "test-key",
          },
        },
        interceptors: {
          response: {
            use: jest.fn(),
          },
        },
        get: jest.fn().mockResolvedValue({ data: {} }),
        post: jest.fn().mockResolvedValue({ data: {} }),
        patch: jest.fn().mockResolvedValue({ data: {} }),
        delete: jest.fn().mockResolvedValue({ data: {} }),
      })),
    },
  };
});

describe("API key header", () => {
  const originalFetch = global.fetch;
  const originalKey = process.env.REACT_APP_API_KEY;

  beforeEach(() => {
    jest.resetModules();
    jest.clearAllMocks();
    process.env.REACT_APP_API_KEY = "test-key";
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ rules: [] }),
    });
  });

  afterEach(() => {
    global.fetch = originalFetch;
    process.env.REACT_APP_API_KEY = originalKey;
  });

  it("passes X-API-Key to axios.create as a default header", async () => {
    // jest.resetModules() in beforeEach clears the module registry, so the
    // axios mock factory re-runs and produces a fresh `create` jest.fn().
    // Re-import axios here (after resetModules, alongside api.js) to get the
    // same mock instance that api.js actually calls.
    const { default: freshAxios } = await import("axios");
    await import("./api");
    expect(freshAxios.create).toHaveBeenCalledWith(
      expect.objectContaining({
        headers: expect.objectContaining({ "X-API-Key": "test-key" }),
      })
    );
  });

  it("sends X-API-Key on rules fetch requests", async () => {
    const { getAllRules } = await import("./api");
    await getAllRules();
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/rules"),
      expect.objectContaining({
        headers: expect.objectContaining({ "X-API-Key": "test-key" }),
      })
    );
  });

  it("sends X-API-Key on rule delete requests", async () => {
    const { deleteRule } = await import("./api");
    await deleteRule("Some Merchant");
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/rules/"),
      expect.objectContaining({
        method: "DELETE",
        headers: expect.objectContaining({ "X-API-Key": "test-key" }),
      })
    );
  });
});
