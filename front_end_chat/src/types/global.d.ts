interface Project {
  name: string;
  // Add other project properties as needed
}

declare global {
  interface Window {
    chatConfig: {
      widgetType: string;
      rootElementId: string;
      jwt?: string;
      project?: Project;
      displayFloatingChatIntro?: boolean;
    };
  }
}

export {}; 