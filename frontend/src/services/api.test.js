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

  it("sets X-API-Key as an axios default header", async () => {
    const { api } = await import("./api");
    expect(api.defaults.headers["X-API-Key"]).toBe("test-key");
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
