export function setSelectedProject(project) {
    const main = document.querySelector('[x-ref="main"]');
    if(main && project) {
        Alpine.nextTick(() => {
            setTimeout(() => {Alpine.store('app').selectedProject = project}, 2000)
            
        })
    }
}