# Neurobazaar Platform  
**Jarvis College of Computing and Digital Media - DePaul University**  

Authors and Contributors:
- Alexandru Iulian Orhean 2024 (aorhean@depaul.edu)  
- Huy Quoc Nguyen 2024 (hnguye83@depaul.edu)  

Interactive Visualization Platform for Machine Learning and Data Science Datasets.

## Purpose

This directory serves as an archive for legacy code. The purpose of keeping this code is to provide future reference and historical context about the development of the codebase. However, since this code is outdated, it is unlikely to be updated or maintained, and its functionality cannot be guaranteed.

I will generally archive code here that is no longer in use, has no current relevance, or is superseded by better examples found in the `example` directory.

If you encounter any issues with non-functional code, please reach out to me at hnguye83@depaul.edu. I will try to address any problems, but due to the nature of this archive, I cannot promise that all issues will be fixed or that updates will be made. Contributions from other developers to improve or maintain the code are welcome.

Additionally, the code in this directory has been cleaned and lacks comments. The `example` directory contains updated code with comments and should serve as the primary reference.

### Sub-directories

**vue-client-for-trame-server**

As the name of the directory suggests, the code in this directory was used to verify the possibility of having the trame server and trame client loosely coupled. This code use Vue.js as the client for the trame server. 

If you are wondering why we wanted to loosely couple the trame application, it was mainly because of security. We were initially using an `iframe` to display the trame application and loosely coupled it with Django, but there was many concerns, security being one of the biggest.

**django-integration-with-vue-client**

As the name of the directory suggests, the code in this directory was used to verify the possibility of integrating the vue-client, which was bundled using ViteJS, with Django.

If you want to find more information on how you can do this, I would recommend looking at the github repositories:

- https://github.com/MrBin99/django-vite?tab=readme-ov-file

- https://github.com/MrBin99/django-vite-example/tree/master