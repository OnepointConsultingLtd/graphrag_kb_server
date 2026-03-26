import { useShallow } from "zustand/shallow";
import useChatStore from "../../context/chatStore";
import { useDashboardStore } from "../../context/dashboardStore";
import RenderLabel from "./Form/RenderLabel";
import ModalParent from "./ModalParent";
import ModalTitle from "./ModalTitle";
import { indexWebpage } from "../../lib/apiClient";
import FormAlert from "./Form/FormAlert";
import { ENGINES } from "../../constants/engines";

export const SCRAPE_WEBSITE_DIALOG_ID = "scrape-website-dialog";

function ActionButtons() {
  const { jwt, refreshProjects } = useChatStore(
    useShallow((state) => ({
      jwt: state.jwt,
      refreshProjects: state.refreshProjects,
    })),
  );
  const {
    webpageForScraping,
    webpageForScrapingValid,
    webpageProject,
    webpageProjectValid,
    maxScrollPages,
    maxScrollPagesValid,
    setWebpageForScrapingDialogOpen,
    resetScrapeWebsiteForm,
    setWebpageScrapeSuccessMessage,
    setWebpageScrapeErrorMessage,
    setWebpageScrapeIsSubmitting
  } = useDashboardStore();

  function handleScrapeAndIndexWebsite() {
    if (!webpageForScraping || !webpageProjectValid || !maxScrollPagesValid) {
      return;
    }
    setWebpageScrapeIsSubmitting(true);
    indexWebpage(
      jwt,
      webpageForScraping,
      webpageProject,
      maxScrollPages,
      ENGINES.LIGHTRAG.toLowerCase(),
    )
      .then((json) => {
        setWebpageScrapeSuccessMessage(json.message);
        refreshProjects();
        resetScrapeWebsiteForm();
      })
      .catch((error) => {
        setWebpageScrapeErrorMessage(error.message);
      })
      .finally(() => {
        setWebpageScrapeIsSubmitting(false);
      });
  }

  return (
    <div className="flex space-x-3 mt-6">
      <button
        onClick={() => setWebpageForScrapingDialogOpen(false)}
        className="flex-1 cursor-pointer bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-md transition-colors duration-200"
      >
        Cancel
      </button>
      <button
        onClick={handleScrapeAndIndexWebsite}
        className="flex-1 cursor-pointer bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
        disabled={
          !webpageForScrapingValid ||
          !webpageProjectValid ||
          !maxScrollPagesValid
        }
      >
        Scrape and Index Website
      </button>
    </div>
  );
}

function ScrapeWebsiteForm() {
  const {
    webpageProject,
    webpageProjectValid,
    webpageProjectTouched,
    setWebpageProject,
    maxScrollPages,
    maxScrollPagesValid,
    setMaxScrollPages,
    webpageForScraping,
    webpageForScrapingTouched,
    webpageForScrapingValid,
    setWebpageForScraping,
  } = useDashboardStore();

  console.log("webpageProjectTouched", webpageProjectTouched);

  return (
    <form className="space-y-4 mt-4">
      {/* Project field */}
      <div>
        <RenderLabel label="Project Name" htmlFor="webpageProject" />
        <input
          id="webpageProject"
          type="text"
          className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring 
            ${webpageProjectValid || !webpageProjectTouched ? "border-gray-300 focus:ring-blue-500" : "border-red-400 focus:ring-red-500"}`}
          value={webpageProject}
          onChange={(e) => setWebpageProject(e.target.value)}
          placeholder="Enter project name"
        />
        {!webpageProjectValid && webpageProjectTouched && (
          <p className="text-xs text-red-500 mt-1">
            Project name must be at least 3 characters long.
          </p>
        )}
      </div>
      {/* Max scroll pages field */}
      <div>
        <RenderLabel label="Max Scroll Pages" htmlFor="maxScrollPages" />
        <input
          id="maxScrollPages"
          type="number"
          min={1}
          max={100}
          className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring 
          ${maxScrollPagesValid ? "border-gray-300 focus:ring-blue-500" : "border-red-400 focus:ring-red-500"}`}
          value={maxScrollPages}
          onChange={(e) => setMaxScrollPages(Number(e.target.value))}
          placeholder="Enter number of pages (1-100)"
        />
        {!maxScrollPagesValid && (
          <p className="text-xs text-red-500 mt-1">
            Scroll pages must be between 1 and 100.
          </p>
        )}
      </div>
      {/* Webpage for scraping field */}
      <div>
        <RenderLabel
          label="Website URL To Scrape"
          htmlFor="webpageForScraping"
        />
        <input
          id="webpageForScraping"
          type="text"
          className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring 
            ${webpageForScrapingValid || !webpageForScrapingTouched ? "border-gray-300 focus:ring-blue-500" : "border-red-400 focus:ring-red-500"}`}
          value={webpageForScraping || ""}
          onChange={(e) => setWebpageForScraping(e.target.value)}
          placeholder="https://example.com"
        />
        {!webpageForScrapingValid && webpageForScrapingTouched && (
          <p className="text-xs text-red-500 mt-1">
            Please enter a valid URL starting with https://
          </p>
        )}
      </div>
    </form>
  );
}

export default function ScrapeWebsiteDialog() {
  const {
    setWebpageForScrapingDialogOpen,
    webpageScrapeErrorMessage,
    webpageScrapeSuccessMessage,
    webpageScrapeIsSubmitting,
  } = useDashboardStore();
  return (
    <ModalParent
      id={SCRAPE_WEBSITE_DIALOG_ID}
      onClose={() => setWebpageForScrapingDialogOpen(false)}
    >
      <div onClick={(e) => e.stopPropagation()}>
        <ModalTitle title="Scrape and Index Website" />
        <ScrapeWebsiteForm />
        {webpageScrapeIsSubmitting && (
          <div className="flex items-center gap-2 mt-3 text-sm text-gray-400">
            <span className="loading loading-spinner loading-sm"></span>
            Scraping and indexing…
          </div>
        )}
        <FormAlert message={webpageScrapeErrorMessage} type="error" />
        <FormAlert message={webpageScrapeSuccessMessage} type="success" />
        <ActionButtons />
      </div>
    </ModalParent>
  );
}
