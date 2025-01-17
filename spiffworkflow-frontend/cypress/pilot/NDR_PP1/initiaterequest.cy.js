
//Software and License - Without Files
describe('Initiate a Request - Without Files', () => {
    Cypress._.times(1, () => {
        //Submit a Software and License request - Without Files
        it('Submit a Software and License request', () => {
            let username = Cypress.env('requestor_username');
            let password = Cypress.env('requestor_password');
            cy.log('=====username : ' + username);
            cy.log('=====password : ' + password);

            cy.login(username, password);
            cy.visit('/');

            cy.contains('Start New +').click();
            cy.contains('Request Goods or Services');

            cy.runPrimaryBpmnFile(true);

            /*            cy.contains('Please select the type of request to start the process.');
                        // wait a second to ensure we can click the radio button
            
                        cy.wait(2000);
                        cy.get('input#root-procurement').click();
                        cy.wait(2000);
            
            
                        cy.get('button')
                            .contains(/^Submit$/)
                            .click();
            */

            cy.contains(
                'Request Goods or Services',
                { timeout: 60000 }
            );

            cy.url().then((currentUrl) => {
                // if url is "/tasks/8/d37c2f0f-016a-4066-b669-e0925b759560"
                // extract the digits after /tasks
                const processInstanceId = currentUrl.match(/(?<=\/tasks\/)\d+/)[0];
                cy.log('==###############===processInstanceId : ', processInstanceId);
                let projectId = Cypress.env('project_id');
                cy.wait(2000);
                cy.get('#root_project').select(projectId);
                cy.get('#root_category').select('soft_and_lic');
                cy.get('#root_purpose').clear().type('Sware\nA software license is a document that provides legally binding guidelines for the use and distribution of software.\nSoftware licenses typically provide end users with the right to one or more copies of the software without violating copyrights');
                cy.get('#root_criticality').select('High');
                cy.get('#root_period').clear().type('25-11-2025');
                cy.get('body').click();
                cy.get('#root_vendor').clear().type('Microsoft');
                cy.get('#root_payment_method').select('Reimbursement');
                /* cy.get('button')
                     .contains(/^Submit$/)
                     .click();
 
                 cy.contains('Task: Enter NDR Items', { timeout: 60000 });
 */
                //item 0
                cy.get('#root_item_0_sub_category').select('op_src');
                cy.get('#root_item_0_item_name').clear().type('Open source software is code that is designed to be publicly accessible anyone can see, modify, END');
                cy.get('#root_item_0_qty').clear().type('2');
                cy.get('#root_item_0_currency_type').select('Crypto');
                cy.get('#root_item_0_currency').select('SNT');
                cy.get('#root_item_0_unit_price').type('1915');


                cy.get('#root_item > div:nth-child(3) > p > button').click();

                //item 1
                cy.get('#root_item_1_sub_category').select('lic_and_sub');
                cy.get('#root_item_1_item_name').clear().type('A software license is a document that provides legally binding guidelines for the use and distri END');
                cy.get('#root_item_1_qty').clear().type('1');
                cy.get('#root_item_1_currency_type').select('Fiat');
                cy.get('#root_item_1_currency').select('AED');
                cy.get('#root_item_1_unit_price').type('4500');


                cy.get('button')
                    .contains(/^Submit$/)
                    .click();

                cy.contains(
                    'Review and provide any supporting information or files for your request.',
                    { timeout: 60000 }
                );

                cy.get('.cds--text-area__wrapper').find('#root').type('2021 Newest HP 17.3 inch FHD Laptop, AMD Ryzen 5 5500U 6core(Beat i7-1160G7, up to 4.0GHz),16GB RAM, 1TB PCIe SSD, Bluetooth 4.2, WiFi, HDMI, USB-A&C, Windows 10 S, w/Ghost Manta Accessories, Silver\nhttps://www.amazon.com/HP-i7-11G7-Bluetooth-Windows');

                cy.contains('Submit the Request').click();

                cy.get('input[value="Submit the Request"]').click();


                cy.get('button')
                    .contains(/^Submit$/)
                    .click();

                cy.get('button')
                    .contains(/^Return to Home$/)
                    .click();

                cy.contains('Started by me', { timeout: 60000 });
                cy.logout();
                cy.wait(2000);
            });
        });

        //Submit a Software and License request - Without Files and with mandatory fields only
        it('Submit a Software and License request - Without Files and with mandatory fields only', () => {
            let username = Cypress.env('requestor_username');
            let password = Cypress.env('requestor_password');
            cy.log('=====username : ' + username);
            cy.log('=====password : ' + password);

            cy.login(username, password);
            cy.visit('/');

            cy.contains('Start New +').click();
            cy.contains('Request Goods or Services');

            cy.runPrimaryBpmnFile(true);

            /*            cy.contains('Please select the type of request to start the process.');
                        // wait a second to ensure we can click the radio button
            
                        cy.wait(2000);
                        cy.get('input#root-procurement').click();
                        cy.wait(2000);
            
            
                        cy.get('button')
                            .contains(/^Submit$/)
                            .click();
            */

            cy.contains(
                'Request Goods or Services',
                { timeout: 60000 }
            );

            cy.url().then((currentUrl) => {
                // if url is "/tasks/8/d37c2f0f-016a-4066-b669-e0925b759560"
                // extract the digits after /tasks
                const processInstanceId = currentUrl.match(/(?<=\/tasks\/)\d+/)[0];
                cy.log('==###############===processInstanceId : ', processInstanceId);
                let projectId = Cypress.env('project_id');
                cy.wait(2000);
                cy.get('#root_project').select(projectId);
                cy.get('#root_category').select('soft_and_lic');
                cy.get('#root_purpose').clear().type('Need to buy a Software');
                cy.get('#root_criticality').select('High');
                cy.get('#root_period').clear().type('24-11-2025');
                cy.get('body').click();
                //cy.get('#root_vendor').clear().type('Embassar');
                //cy.get('#root_payment_method').select('Reimbursement');
                /* cy.get('button')
                     .contains(/^Submit$/)
                     .click();
 
                 cy.contains('Task: Enter NDR Items', { timeout: 60000 });
 */
                cy.get('#root_item_0_sub_category').select('op_src');
                cy.get('#root_item_0_item_name').clear().type('Open source software');
                cy.get('#root_item_0_qty').clear().type('2');
                cy.get('#root_item_0_currency_type').select('Fiat');
                cy.get('#root_item_0_currency').select('USD');
                cy.get('#root_item_0_unit_price').type('550');


                cy.get('button')
                    .contains(/^Submit$/)
                    .click();

                cy.contains(
                    'Review and provide any supporting information or files for your request.',
                    { timeout: 60000 }
                );

                //cy.get('.cds--text-area__wrapper').find('#root').type('For professionals working in the professional services, ‘consultant’ and advisor’ are often used and fall under common terminology. Consultancy.uk zooms in on this field to get a closer look. \n https://www.consultancy.uk/career/what-is-consulting');

                cy.contains('Submit the Request').click();

                cy.get('input[value="Submit the Request"]').click();


                cy.get('button')
                    .contains(/^Submit$/)
                    .click();

                cy.get('button')
                    .contains(/^Return to Home$/)
                    .click();

                cy.contains('Started by me', { timeout: 60000 });
                cy.logout();
                cy.wait(2000);

            });
        });

        //Edit a Software and License request - Without Files
        it('Edit a Software and License request', () => {
            let username = Cypress.env('requestor_username');
            let password = Cypress.env('requestor_password');
            cy.log('=====username : ' + username);
            cy.log('=====password : ' + password);

            cy.login(username, password);
            cy.visit('/');

            cy.contains('Start New +').click();
            cy.contains('Request Goods or Services');

            cy.runPrimaryBpmnFile(true);

            /*            cy.contains('Please select the type of request to start the process.');
                        // wait a second to ensure we can click the radio button
            
                        cy.wait(2000);
                        cy.get('input#root-procurement').click();
                        cy.wait(2000);
            
            
                        cy.get('button')
                            .contains(/^Submit$/)
                            .click();
            */

            cy.contains(
                'Request Goods or Services',
                { timeout: 60000 }
            );

            cy.url().then((currentUrl) => {
                // if url is "/tasks/8/d37c2f0f-016a-4066-b669-e0925b759560"
                // extract the digits after /tasks
                const processInstanceId = currentUrl.match(/(?<=\/tasks\/)\d+/)[0];
                cy.log('==###############===processInstanceId : ', processInstanceId);
                let projectId = Cypress.env('project_id');
                cy.wait(2000);
                cy.get('#root_project').select(projectId);
                cy.get('#root_category').select('soft_and_lic');
                cy.get('#root_purpose').clear().type('Sware\nA software license is a document that provides legally binding guidelines for the use and distribution of software.\nSoftware licenses typically provide end users with the right to one or more copies of the software without violating copyrights');
                cy.get('#root_criticality').select('High');
                cy.get('#root_period').clear().type('25-11-2025');
                cy.get('body').click();
                cy.get('#root_vendor').clear().type('Microsoft');
                cy.get('#root_payment_method').select('Reimbursement');
                /* cy.get('button')
                     .contains(/^Submit$/)
                     .click();
 
                 cy.contains('Task: Enter NDR Items', { timeout: 60000 });
 */
                //item 0
                cy.get('#root_item_0_sub_category').select('op_src');
                cy.get('#root_item_0_item_name').clear().type('Open source software is code that is designed to be publicly accessible anyone can see, modify, END');
                cy.get('#root_item_0_qty').clear().type('2');
                cy.get('#root_item_0_currency_type').select('Crypto');
                cy.get('#root_item_0_currency').select('SNT');
                cy.get('#root_item_0_unit_price').type('1915');


                cy.get('#root_item > div:nth-child(3) > p > button').click();

                //item 1
                cy.get('#root_item_1_sub_category').select('lic_and_sub');
                cy.get('#root_item_1_item_name').clear().type('A software license is a document that provides legally binding guidelines for the use and distri END');
                cy.get('#root_item_1_qty').clear().type('1');
                cy.get('#root_item_1_currency_type').select('Fiat');
                cy.get('#root_item_1_currency').select('AED');
                cy.get('#root_item_1_unit_price').type('4500');


                cy.get('button')
                    .contains(/^Submit$/)
                    .click();

                cy.contains(
                    'Review and provide any supporting information or files for your request.',
                    { timeout: 60000 }
                );

                cy.get('.cds--text-area__wrapper').find('#root').type('2021 Newest HP 17.3 inch FHD Laptop, AMD Ryzen 5 5500U 6core(Beat i7-1160G7, up to 4.0GHz),16GB RAM, 1TB PCIe SSD, Bluetooth 4.2, WiFi, HDMI, USB-A&C, Windows 10 S, w/Ghost Manta Accessories, Silver\nhttps://www.amazon.com/HP-i7-11G7-Bluetooth-Windows');

                cy.contains('Edit the Request').click();

                cy.get('input[value="Edit the Request"]').click();


                cy.get('button')
                    .contains(/^Submit$/)
                    .click();




                //Form 1
                cy.contains('Task: Submit Details', { timeout: 60000 });
                cy.wait(2000);
                cy.get('button')
                    .contains(/^Submit$/)
                    .click();
                //Form 2      
                /*cy.contains('Task: Enter NDR Items', { timeout: 60000 });
                cy.get('button')
                  .contains(/^Submit$/)
                  .click();*/
                //Form 3
                cy.contains(
                    'Task: Review the Request',
                    { timeout: 60000 });

                cy.get('.cds--text-area__wrapper').find('#root').type('EDITING INFO : 2021 Newest HP 17.3 inch FHD Laptop, AMD Ryzen 5 5500U 6core(Beat i7-1160G7, up to 4.0GHz),16GB RAM, 1TB PCIe SSD, Bluetooth 4.2, WiFi, HDMI, USB-A&C, Silver\nhttps://www.amazon.com/HP-i7-11G7-Bluetooth-Windows');

                cy.contains('Submit the Request').click();
                cy.get('input[value="Submit the Request"]').click();

                cy.get('button')
                    .contains(/^Submit$/)
                    .click();

                cy.get('button')
                    .contains(/^Return to Home$/)
                    .click();

                cy.contains('Started by me', { timeout: 60000 });
                cy.logout();
                cy.wait(2000);
            });
        });

        //Save as Draft a Software and License request - Without Files
        it.only('Save as Draft a Software and License request', () => {
            let username = Cypress.env('requestor_username');
            let password = Cypress.env('requestor_password');
            cy.log('=====username : ' + username);
            cy.log('=====password : ' + password);

            cy.login(username, password);
            cy.visit('/');

            cy.contains('Start New +').click();
            cy.contains('Request Goods or Services');

            cy.runPrimaryBpmnFile(true);

            /*            cy.contains('Please select the type of request to start the process.');
                        // wait a second to ensure we can click the radio button
            
                        cy.wait(2000);
                        cy.get('input#root-procurement').click();
                        cy.wait(2000);
            
            
                        cy.get('button')
                            .contains(/^Submit$/)
                            .click();
            */

            cy.contains(
                'Request Goods or Services',
                { timeout: 60000 }
            );

            cy.url().then((currentUrl) => {
                // if url is "/tasks/8/d37c2f0f-016a-4066-b669-e0925b759560"
                // extract the digits after /tasks
                const processInstanceId = currentUrl.match(/(?<=\/tasks\/)\d+/)[0];
                cy.log('==###############===processInstanceId : ', processInstanceId);
                let projectId = Cypress.env('project_id');
                cy.wait(2000);
                cy.get('#root_project').select(projectId);
                cy.get('#root_category').select('soft_and_lic');
                cy.get('#root_purpose').clear().type('Sware\nA software license is a document that provides legally binding guidelines for the use and distribution of software.\nSoftware licenses typically provide end users with the right to one or more copies of the software without violating copyrights');
                cy.get('#root_criticality').select('High');
                cy.get('#root_period').clear().type('25-11-2025');
                cy.get('body').click();
                cy.get('#root_vendor').clear().type('Microsoft');
                cy.get('#root_payment_method').select('Reimbursement');
                /* cy.get('button')
                     .contains(/^Submit$/)
                     .click();
 
                 cy.contains('Task: Enter NDR Items', { timeout: 60000 });
 */
                //item 0
                cy.get('#root_item_0_sub_category').select('op_src');
                cy.get('#root_item_0_item_name').clear().type('Open source software is code that is designed to be publicly accessible anyone can see, modify, END');
                cy.get('#root_item_0_qty').clear().type('2');
                cy.get('#root_item_0_currency_type').select('Crypto');
                cy.get('#root_item_0_currency').select('SNT');
                cy.get('#root_item_0_unit_price').type('1915');


                cy.get('#root_item > div:nth-child(3) > p > button').click();

                //item 1
                cy.get('#root_item_1_sub_category').select('lic_and_sub');
                cy.get('#root_item_1_item_name').clear().type('A software license is a document that provides legally binding guidelines for the use and distri END');
                cy.get('#root_item_1_qty').clear().type('1');
                cy.get('#root_item_1_currency_type').select('Fiat');
                cy.get('#root_item_1_currency').select('AED');
                cy.get('#root_item_1_unit_price').type('4500');

                cy.get('button')
                    .contains(/^Save as draft$/)
                    .click();

                cy.get('button')
                    .contains(/^Return to Home$/)
                    .click();

                cy.contains('Started by me', { timeout: 60000 });
                cy.logout();


            });
        });

        //Cancel a Software and License request 1- Without Files
        it('Cancel a Software and License request 1', () => {
            let username = Cypress.env('requestor_username');
            let password = Cypress.env('requestor_password');
            cy.log('=====username : ' + username);
            cy.log('=====password : ' + password);

            cy.login(username, password);
            cy.visit('/');

            cy.contains('Start New +').click();
            cy.contains('Request Goods or Services');

            cy.runPrimaryBpmnFile(true);

            /*            cy.contains('Please select the type of request to start the process.');
                        // wait a second to ensure we can click the radio button
            
                        cy.wait(2000);
                        cy.get('input#root-procurement').click();
                        cy.wait(2000);
            
            
                        cy.get('button')
                            .contains(/^Submit$/)
                            .click();
            */

            cy.contains(
                'Request Goods or Services',
                { timeout: 60000 }
            );

            cy.url().then((currentUrl) => {
                // if url is "/tasks/8/d37c2f0f-016a-4066-b669-e0925b759560"
                // extract the digits after /tasks
                const processInstanceId = currentUrl.match(/(?<=\/tasks\/)\d+/)[0];
                cy.log('==###############===processInstanceId : ', processInstanceId);
                let projectId = Cypress.env('project_id');
                cy.wait(2000);
                cy.get('#root_project').select(projectId);
                cy.get('#root_category').select('soft_and_lic');
                cy.get('#root_purpose').clear().type('Sware\nA software license is a document that provides legally binding guidelines for the use and distribution of software.\nSoftware licenses typically provide end users with the right to one or more copies of the software without violating copyrights');
                cy.get('#root_criticality').select('High');
                cy.get('#root_period').clear().type('25-11-2025');
                cy.get('body').click();
                cy.get('#root_vendor').clear().type('Microsoft');
                cy.get('#root_payment_method').select('Reimbursement');
                /* cy.get('button')
                     .contains(/^Submit$/)
                     .click();
 
                 cy.contains('Task: Enter NDR Items', { timeout: 60000 });
 */
                //item 0
                cy.get('#root_item_0_sub_category').select('op_src');
                cy.get('#root_item_0_item_name').clear().type('Open source software is code that is designed to be publicly accessible anyone can see, modify, END');
                cy.get('#root_item_0_qty').clear().type('2');
                cy.get('#root_item_0_currency_type').select('Crypto');
                cy.get('#root_item_0_currency').select('SNT');
                cy.get('#root_item_0_unit_price').type('1915');


                cy.get('#root_item > div:nth-child(3) > p > button').click();

                //item 1
                cy.get('#root_item_1_sub_category').select('lic_and_sub');
                cy.get('#root_item_1_item_name').clear().type('A software license is a document that provides legally binding guidelines for the use and distri END');
                cy.get('#root_item_1_qty').clear().type('1');
                cy.get('#root_item_1_currency_type').select('Fiat');
                cy.get('#root_item_1_currency').select('AED');
                cy.get('#root_item_1_unit_price').type('4500');

                cy.get('#root-Yes').click();

                cy.get('button')
                    .contains(/^Submit$/)
                    .click();

                cy.get('button')
                    .contains(/^Return to Home$/)
                    .click();

                cy.contains('Started by me', { timeout: 60000 });
                cy.logout();


            });
        });

        //Cancel a Software and License request 2- Without Files
        it('Cancel a Software and License request 2', () => {
            let username = Cypress.env('requestor_username');
            let password = Cypress.env('requestor_password');
            cy.log('=====username : ' + username);
            cy.log('=====password : ' + password);

            cy.login(username, password);
            cy.visit('/');

            cy.contains('Start New +').click();
            cy.contains('Request Goods or Services');

            cy.runPrimaryBpmnFile(true);

            /*            cy.contains('Please select the type of request to start the process.');
                        // wait a second to ensure we can click the radio button
            
                        cy.wait(2000);
                        cy.get('input#root-procurement').click();
                        cy.wait(2000);
            
            
                        cy.get('button')
                            .contains(/^Submit$/)
                            .click();
            */

            cy.contains(
                'Request Goods or Services',
                { timeout: 60000 }
            );

            cy.url().then((currentUrl) => {
                // if url is "/tasks/8/d37c2f0f-016a-4066-b669-e0925b759560"
                // extract the digits after /tasks
                const processInstanceId = currentUrl.match(/(?<=\/tasks\/)\d+/)[0];
                cy.log('==###############===processInstanceId : ', processInstanceId);
                let projectId = Cypress.env('project_id');
                cy.wait(2000);
                cy.get('#root_project').select(projectId);
                cy.get('#root_category').select('soft_and_lic');
                cy.get('#root_purpose').clear().type('Sware\nA software license is a document that provides legally binding guidelines for the use and distribution of software.\nSoftware licenses typically provide end users with the right to one or more copies of the software without violating copyrights');
                cy.get('#root_criticality').select('High');
                cy.get('#root_period').clear().type('25-11-2025');
                cy.get('body').click();
                cy.get('#root_vendor').clear().type('Microsoft');
                cy.get('#root_payment_method').select('Reimbursement');
                /* cy.get('button')
                     .contains(/^Submit$/)
                     .click();
 
                 cy.contains('Task: Enter NDR Items', { timeout: 60000 });
 */
                //item 0
                cy.get('#root_item_0_sub_category').select('op_src');
                cy.get('#root_item_0_item_name').clear().type('Open source software is code that is designed to be publicly accessible anyone can see, modify, END');
                cy.get('#root_item_0_qty').clear().type('2');
                cy.get('#root_item_0_currency_type').select('Crypto');
                cy.get('#root_item_0_currency').select('SNT');
                cy.get('#root_item_0_unit_price').type('1915');


                cy.get('#root_item > div:nth-child(3) > p > button').click();

                //item 1
                cy.get('#root_item_1_sub_category').select('lic_and_sub');
                cy.get('#root_item_1_item_name').clear().type('A software license is a document that provides legally binding guidelines for the use and distri END');
                cy.get('#root_item_1_qty').clear().type('1');
                cy.get('#root_item_1_currency_type').select('Fiat');
                cy.get('#root_item_1_currency').select('AED');
                cy.get('#root_item_1_unit_price').type('4500');


                cy.get('button')
                    .contains(/^Submit$/)
                    .click();

                cy.contains(
                    'Review and provide any supporting information or files for your request.',
                    { timeout: 60000 }
                );

                cy.get('.cds--text-area__wrapper').find('#root').type('2021 Newest HP 17.3 inch FHD Laptop, AMD Ryzen 5 5500U 6core(Beat i7-1160G7, up to 4.0GHz),16GB RAM, 1TB PCIe SSD, Bluetooth 4.2, WiFi, HDMI, USB-A&C, Windows 10 S, w/Ghost Manta Accessories, Silver\nhttps://www.amazon.com/HP-i7-11G7-Bluetooth-Windows');

                cy.contains('Cancel the Request').click();

                cy.get('input[value="Cancel the Request"]').click();

                cy.get('button')
                    .contains(/^Submit$/)
                    .click();

                cy.get('button')
                    .contains(/^Return to Home$/)
                    .click();

                cy.contains('Started by me', { timeout: 60000 });
                cy.logout();


            });
        });
    });
});

//Software and License - With Files
describe('Initiate a Request - With Files', () => {
    Cypress._.times(1, () => {
        //Submit a Software and License request - Without Files
        it('Submit a Software and License request', () => {
            let username = Cypress.env('requestor_username');
            let password = Cypress.env('requestor_password');
            cy.log('=====username : ' + username);
            cy.log('=====password : ' + password);

            cy.login(username, password);
            cy.visit('/');

            cy.contains('Start New +').click();
            cy.contains('Request Goods or Services');

            cy.runPrimaryBpmnFile(true);

            /*            cy.contains('Please select the type of request to start the process.');
                        // wait a second to ensure we can click the radio button
            
                        cy.wait(2000);
                        cy.get('input#root-procurement').click();
                        cy.wait(2000);
            
            
                        cy.get('button')
                            .contains(/^Submit$/)
                            .click();
            */

            cy.contains(
                'Request Goods or Services',
                { timeout: 60000 }
            );

            cy.url().then((currentUrl) => {
                // if url is "/tasks/8/d37c2f0f-016a-4066-b669-e0925b759560"
                // extract the digits after /tasks
                const processInstanceId = currentUrl.match(/(?<=\/tasks\/)\d+/)[0];
                cy.log('==###############===processInstanceId : ', processInstanceId);
                let projectId = Cypress.env('project_id');
                cy.wait(2000);
                cy.get('#root_project').select(projectId);
                cy.get('#root_category').select('soft_and_lic');
                cy.get('#root_purpose').clear().type('Sware\nA software license is a document that provides legally binding guidelines for the use and distribution of software.\nSoftware licenses typically provide end users with the right to one or more copies of the software without violating copyrights');
                cy.get('#root_criticality').select('High');
                cy.get('#root_period').clear().type('15-11-2035');
                cy.get('body').click();
                cy.get('#root_vendor').clear().type('Microsoft Corp');
                cy.get('#root_payment_method').select('Reimbursement');
                /* cy.get('button')
                     .contains(/^Submit$/)
                     .click();
 
                 cy.contains('Task: Enter NDR Items', { timeout: 60000 });
 */
                //item 0
                cy.get('#root_item_0_sub_category').select('op_src');
                cy.get('#root_item_0_item_name').clear().type('Open source software is developed in a decentralized and collaborative way');
                cy.get('#root_item_0_qty').clear().type('2');
                cy.get('#root_item_0_currency_type').select('Fiat');
                cy.get('#root_item_0_currency').select('JPY');
                cy.get('#root_item_0_unit_price').type('2416');

                cy.get('#root_item > div:nth-child(3) > p > button').click();

                //item 1
                cy.get('#root_item_1_sub_category').select('lic_and_sub');
                cy.get('#root_item_1_item_name').clear().type('A software license is a document that provides legally binding guidelines for the use and distri END');
                cy.get('#root_item_1_qty').clear().type('1');
                cy.get('#root_item_1_currency_type').select('Fiat');
                cy.get('#root_item_1_currency').select('INR');
                cy.get('#root_item_1_unit_price').type('4500');


                cy.get('button')
                    .contains(/^Submit$/)
                    .click();

                cy.contains(
                    'Review and provide any supporting information or files for your request.',
                    { timeout: 60000 }
                );

                cy.get('.cds--text-area__wrapper').find('#root').type('Open source software is developed in a decentralized and collaborative way, relying on peer review and community production. Open source software is often cheaper more flexible. \nhttps://www.redhat.com/en');

                cy.get('#root > div:nth-child(3) > p > button').click();

                cy.get("input[type=file]")
                    .attachFile(['lorem-ipsum.pdf']);
                cy.wait(1000);

                cy.get('#root > div:nth-child(3) > p > button').click();
                cy.wait(1000);

                cy.get('#root > div.row.array-item-list > div:nth-child(2) > div > div.cds--sm\\:col-span-1.cds--md\\:col-span-1.cds--lg\\:col-span-1.cds--css-grid-column > div > div > button.btn.btn-default.array-item-move-up > svg').click();
                cy.wait(1000);
                cy.get("input[type=file]")
                    .attachFile(['png-5mb-1.png']);
                cy.wait(1000);

                cy.get('#root > div:nth-child(3) > p > button').click();
                cy.wait(1000);

                cy.get('#root > div.row.array-item-list > div:nth-child(3) > div > div.cds--sm\\:col-span-1.cds--md\\:col-span-1.cds--lg\\:col-span-1.cds--css-grid-column > div > div > button.btn.btn-default.array-item-move-up > svg').click();
                cy.wait(1000);
                cy.get('#root > div.row.array-item-list > div:nth-child(2) > div > div.cds--sm\\:col-span-1.cds--md\\:col-span-1.cds--lg\\:col-span-1.cds--css-grid-column > div > div > button.btn.btn-default.array-item-move-up > svg').click();
                cy.wait(1000);

                cy.get("input[type=file]")
                    .attachFile(['Free_Test_Data_1MB_PDF.pdf']);
                cy.wait(1000);

                cy.get('#root > div:nth-child(3) > p > button').click();
                cy.wait(1000);

                cy.get('#root > div.row.array-item-list > div:nth-child(4) > div > div.cds--sm\\:col-span-1.cds--md\\:col-span-1.cds--lg\\:col-span-1.cds--css-grid-column > div > div > button.btn.btn-default.array-item-move-up > svg').click();
                cy.wait(1000);
                cy.get('#root > div.row.array-item-list > div:nth-child(3) > div > div.cds--sm\\:col-span-1.cds--md\\:col-span-1.cds--lg\\:col-span-1.cds--css-grid-column > div > div > button.btn.btn-default.array-item-move-up > svg').click();
                cy.wait(1000);
                cy.get('#root > div.row.array-item-list > div:nth-child(2) > div > div.cds--sm\\:col-span-1.cds--md\\:col-span-1.cds--lg\\:col-span-1.cds--css-grid-column > div > div > button.btn.btn-default.array-item-move-up > svg').click();
                cy.wait(1000);

                cy.get("input[type=file]")
                    .attachFile(['sampletext.txt']);

                cy.wait(2000);

                cy.contains('Submit the Request').click();

                cy.get('input[value="Submit the Request"]').click();


                cy.get('button')
                    .contains(/^Submit$/)
                    .click();

                cy.get('button')
                    .contains(/^Return to Home$/)
                    .click();


                cy.contains('Started by me', { timeout: 60000 });
                cy.logout();
                cy.wait(2000);

            });
        });

        //Submit a Software and License request - With Files and Multiple items
        it('Submit a Software and License request - With Files and Multiple items', () => {
            let username = Cypress.env('requestor_username');
            let password = Cypress.env('requestor_password');
            cy.log('=====username : ' + username);
            cy.log('=====password : ' + password);

            cy.login(username, password);
            cy.visit('/');

            cy.contains('Start New +').click();
            cy.contains('Request Goods or Services');

            cy.runPrimaryBpmnFile(true);

            /*            cy.contains('Please select the type of request to start the process.');
                        // wait a second to ensure we can click the radio button
            
                        cy.wait(2000);
                        cy.get('input#root-procurement').click();
                        cy.wait(2000);
            
            
                        cy.get('button')
                            .contains(/^Submit$/)
                            .click();
            */

            cy.contains(
                'Request Goods or Services',
                { timeout: 60000 }
            );

            cy.url().then((currentUrl) => {
                // if url is "/tasks/8/d37c2f0f-016a-4066-b669-e0925b759560"
                // extract the digits after /tasks
                const processInstanceId = currentUrl.match(/(?<=\/tasks\/)\d+/)[0];
                cy.log('==###############===processInstanceId : ', processInstanceId);
                let projectId = Cypress.env('project_id');
                cy.wait(2000);
                cy.get('#root_project').select(projectId);
                cy.get('#root_category').select('soft_and_lic');
                cy.get('#root_purpose').clear().type('Software licenses typically are proprietary, free or open source. The distinguishing feature is the terms under which users may redistribute or copy the software for future development or use.');
                cy.get('#root_criticality').select('High');
                cy.get('#root_period').clear().type('25-11-2025');
                cy.get('body').click();
                cy.get('#root_vendor').clear().type('Meta Corp');
                cy.get('#root_payment_method').select('Reimbursement');
                /* cy.get('button')
                     .contains(/^Submit$/)
                     .click();
 
                 cy.contains('Task: Enter NDR Items', { timeout: 60000 });
 */

                //item 0
                cy.get('#root_item_0_sub_category').select('op_src');
                cy.get('#root_item_0_item_name').clear().type('Definition. Open source software (OSS) is software that is distributed with its source code');
                cy.get('#root_item_0_qty').clear().type('1');
                cy.get('#root_item_0_currency_type').select('Fiat');
                cy.get('#root_item_0_currency').select('AUD');
                cy.get('#root_item_0_unit_price').type('2416');

                cy.get('#root_item > div:nth-child(3) > p > button').click();

                //item 1
                cy.get('#root_item_1_sub_category').select('lic_and_sub');
                cy.get('#root_item_1_item_name').clear().type('A software license is a document that provides binding guidelines for the use and distribution.');
                cy.get('#root_item_1_qty').clear().type('5');
                cy.get('#root_item_1_currency_type').select('Fiat');
                cy.get('#root_item_1_currency').select('EUR');
                cy.get('#root_item_1_unit_price').type('250');

                cy.get('#root_item > div:nth-child(3) > p > button').click();

                //item 2
                cy.get('#root_item_2_sub_category').select('lic_and_sub');
                cy.get('#root_item_2_item_name').clear().type('Subscription relates to a licensing model that allows users to pay regularly for a computer program');
                cy.get('#root_item_2_qty').clear().type('10');
                cy.get('#root_item_2_currency_type').select('Crypto');
                cy.get('#root_item_2_currency').select('DAI');
                cy.get('#root_item_2_unit_price').type('12500');



                cy.get('button')
                    .contains(/^Submit$/)
                    .click();

                cy.contains(
                    'Review and provide any supporting information or files for your request.',
                    { timeout: 60000 }
                );

                cy.get('.cds--text-area__wrapper').find('#root').type('A software license is a legal instrument (usually by way of contract law, with or without printed material) governing the use or redistribution of software. Under United States copyright law, all software is copyright protected.');

                cy.get('#root > div:nth-child(3) > p > button').click();

                cy.get("input[type=file]")
                    .attachFile(['lorem-ipsum.pdf']);
                cy.wait(1000);

                cy.get('#root > div:nth-child(3) > p > button').click();
                cy.wait(1000);

                cy.get('#root > div.row.array-item-list > div:nth-child(2) > div > div.cds--sm\\:col-span-1.cds--md\\:col-span-1.cds--lg\\:col-span-1.cds--css-grid-column > div > div > button.btn.btn-default.array-item-move-up > svg').click();
                cy.wait(1000);
                cy.get("input[type=file]")
                    .attachFile(['png-5mb-1.png']);
                cy.wait(1000);

                cy.get('#root > div:nth-child(3) > p > button').click();
                cy.wait(1000);

                cy.get('#root > div.row.array-item-list > div:nth-child(3) > div > div.cds--sm\\:col-span-1.cds--md\\:col-span-1.cds--lg\\:col-span-1.cds--css-grid-column > div > div > button.btn.btn-default.array-item-move-up > svg').click();
                cy.wait(1000);
                cy.get('#root > div.row.array-item-list > div:nth-child(2) > div > div.cds--sm\\:col-span-1.cds--md\\:col-span-1.cds--lg\\:col-span-1.cds--css-grid-column > div > div > button.btn.btn-default.array-item-move-up > svg').click();
                cy.wait(1000);

                cy.get("input[type=file]")
                    .attachFile(['Free_Test_Data_1MB_PDF.pdf']);
                cy.wait(1000);

                cy.get('#root > div:nth-child(3) > p > button').click();
                cy.wait(1000);

                cy.get('#root > div.row.array-item-list > div:nth-child(4) > div > div.cds--sm\\:col-span-1.cds--md\\:col-span-1.cds--lg\\:col-span-1.cds--css-grid-column > div > div > button.btn.btn-default.array-item-move-up > svg').click();
                cy.wait(1000);
                cy.get('#root > div.row.array-item-list > div:nth-child(3) > div > div.cds--sm\\:col-span-1.cds--md\\:col-span-1.cds--lg\\:col-span-1.cds--css-grid-column > div > div > button.btn.btn-default.array-item-move-up > svg').click();
                cy.wait(1000);
                cy.get('#root > div.row.array-item-list > div:nth-child(2) > div > div.cds--sm\\:col-span-1.cds--md\\:col-span-1.cds--lg\\:col-span-1.cds--css-grid-column > div > div > button.btn.btn-default.array-item-move-up > svg').click();
                cy.wait(1000);

                cy.get("input[type=file]")
                    .attachFile(['sampletext.txt']);

                cy.wait(2000);

                cy.contains('Submit the Request').click();

                cy.get('input[value="Submit the Request"]').click();


                cy.get('button')
                    .contains(/^Submit$/)
                    .click();

                cy.get('button')
                    .contains(/^Return to Home$/)
                    .click();

                cy.contains('Started by me', { timeout: 60000 });
                cy.logout();
                cy.wait(2000);

            });
        });

        //Edit a Software and License request - With Files
        it('Edit a Software and License request', () => {
            let username = Cypress.env('requestor_username');
            let password = Cypress.env('requestor_password');
            cy.log('=====username : ' + username);
            cy.log('=====password : ' + password);

            cy.login(username, password);
            cy.visit('/');

            cy.contains('Start New +').click();
            cy.contains('Request Goods or Services');

            cy.runPrimaryBpmnFile(true);

            /*            cy.contains('Please select the type of request to start the process.');
                        // wait a second to ensure we can click the radio button
            
                        cy.wait(2000);
                        cy.get('input#root-procurement').click();
                        cy.wait(2000);
            
            
                        cy.get('button')
                            .contains(/^Submit$/)
                            .click();
            */

            cy.contains(
                'Request Goods or Services',
                { timeout: 60000 }
            );

            cy.url().then((currentUrl) => {
                // if url is "/tasks/8/d37c2f0f-016a-4066-b669-e0925b759560"
                // extract the digits after /tasks
                const processInstanceId = currentUrl.match(/(?<=\/tasks\/)\d+/)[0];
                cy.log('==###############===processInstanceId : ', processInstanceId);
                let projectId = Cypress.env('project_id');
                cy.wait(2000);
                cy.get('#root_project').select(projectId);
                cy.get('#root_category').select('soft_and_lic');
                cy.get('#root_purpose').clear().type('Sware\nA software license is a document that provides legally binding guidelines for the use and distribution of software.\nSoftware licenses typically provide end users with the right to one or more copies of the software without violating copyrights');
                cy.get('#root_criticality').select('High');
                cy.get('#root_period').clear().type('25-11-2025');
                cy.get('body').click();
                cy.get('#root_vendor').clear().type('Microsoft');
                cy.get('#root_payment_method').select('Reimbursement');
                /* cy.get('button')
                     .contains(/^Submit$/)
                     .click();
 
                 cy.contains('Task: Enter NDR Items', { timeout: 60000 });
 */
                //item 0
                cy.get('#root_item_0_sub_category').select('op_src');
                cy.get('#root_item_0_item_name').clear().type('Open source software is code that is designed to be publicly accessible anyone can see, modify, END');
                cy.get('#root_item_0_qty').clear().type('2');
                cy.get('#root_item_0_currency_type').select('Crypto');
                cy.get('#root_item_0_currency').select('SNT');
                cy.get('#root_item_0_unit_price').type('1915');


                cy.get('#root_item > div:nth-child(3) > p > button').click();

                //item 1
                cy.get('#root_item_1_sub_category').select('lic_and_sub');
                cy.get('#root_item_1_item_name').clear().type('A software license is a document that provides legally binding guidelines for the use and distri END');
                cy.get('#root_item_1_qty').clear().type('1');
                cy.get('#root_item_1_currency_type').select('Fiat');
                cy.get('#root_item_1_currency').select('AED');
                cy.get('#root_item_1_unit_price').type('4500');


                cy.get('button')
                    .contains(/^Submit$/)
                    .click();

                cy.contains(
                    'Review and provide any supporting information or files for your request.',
                    { timeout: 60000 }
                );

                cy.get('.cds--text-area__wrapper').find('#root').type('2021 Newest HP 17.3 inch FHD Laptop, AMD Ryzen 5 5500U 6core(Beat i7-1160G7, up to 4.0GHz),16GB RAM, 1TB PCIe SSD, Bluetooth 4.2, WiFi, HDMI, USB-A&C, Windows 10 S, w/Ghost Manta Accessories, Silver\nhttps://www.amazon.com/HP-i7-11G7-Bluetooth-Windows');

                cy.get('#root > div:nth-child(3) > p > button').click();

                cy.get("input[type=file]")
                    .attachFile(['lorem-ipsum.pdf']);
                cy.wait(1000);

                cy.get('#root > div:nth-child(3) > p > button').click();
                cy.wait(1000);

                cy.get('#root > div.row.array-item-list > div:nth-child(2) > div > div.cds--sm\\:col-span-1.cds--md\\:col-span-1.cds--lg\\:col-span-1.cds--css-grid-column > div > div > button.btn.btn-default.array-item-move-up > svg').click();
                cy.wait(1000);
                cy.get("input[type=file]")
                    .attachFile(['png-5mb-1.png']);
                cy.wait(1000);

                cy.get('#root > div:nth-child(3) > p > button').click();
                cy.wait(1000);

                cy.get('#root > div.row.array-item-list > div:nth-child(3) > div > div.cds--sm\\:col-span-1.cds--md\\:col-span-1.cds--lg\\:col-span-1.cds--css-grid-column > div > div > button.btn.btn-default.array-item-move-up > svg').click();
                cy.wait(1000);
                cy.get('#root > div.row.array-item-list > div:nth-child(2) > div > div.cds--sm\\:col-span-1.cds--md\\:col-span-1.cds--lg\\:col-span-1.cds--css-grid-column > div > div > button.btn.btn-default.array-item-move-up > svg').click();
                cy.wait(1000);

                cy.get("input[type=file]")
                    .attachFile(['Free_Test_Data_1MB_PDF.pdf']);
                cy.wait(1000);

                cy.get('#root > div:nth-child(3) > p > button').click();
                cy.wait(1000);

                cy.get('#root > div.row.array-item-list > div:nth-child(4) > div > div.cds--sm\\:col-span-1.cds--md\\:col-span-1.cds--lg\\:col-span-1.cds--css-grid-column > div > div > button.btn.btn-default.array-item-move-up > svg').click();
                cy.wait(1000);
                cy.get('#root > div.row.array-item-list > div:nth-child(3) > div > div.cds--sm\\:col-span-1.cds--md\\:col-span-1.cds--lg\\:col-span-1.cds--css-grid-column > div > div > button.btn.btn-default.array-item-move-up > svg').click();
                cy.wait(1000);
                cy.get('#root > div.row.array-item-list > div:nth-child(2) > div > div.cds--sm\\:col-span-1.cds--md\\:col-span-1.cds--lg\\:col-span-1.cds--css-grid-column > div > div > button.btn.btn-default.array-item-move-up > svg').click();
                cy.wait(1000);

                cy.get("input[type=file]")
                    .attachFile(['png-5mb-2.png']);

                cy.wait(2000);


                cy.contains('Edit the Request').click();

                cy.get('input[value="Edit the Request"]').click();


                cy.get('button')
                    .contains(/^Submit$/)
                    .click();


                //Form 1
                cy.contains('Task: Submit Details', { timeout: 60000 });
                cy.wait(2000);
                cy.get('button')
                    .contains(/^Submit$/)
                    .click();
                //Form 2      
                /*cy.contains('Task: Enter NDR Items', { timeout: 60000 });
                cy.get('button')
                  .contains(/^Submit$/)
                  .click();*/
                //Form 3
                cy.contains(
                    'Task: Review the Request',
                    { timeout: 60000 });

                cy.get('.cds--text-area__wrapper').find('#root').type('EDITING INFO : 2021 Newest HP 17.3 inch FHD Laptop, AMD Ryzen 5 5500U 6core(Beat i7-1160G7, up to 4.0GHz),16GB RAM, 1TB PCIe SSD, Bluetooth 4.2, WiFi, HDMI, USB-A&C, Silver\nhttps://www.amazon.com/HP-i7-11G7-Bluetooth-Windows');

                cy.contains('Submit the Request').click();
                cy.get('input[value="Submit the Request"]').click();

                cy.get('button')
                    .contains(/^Submit$/)
                    .click();

                cy.get('button')
                    .contains(/^Return to Home$/)
                    .click();

                cy.contains('Started by me', { timeout: 60000 });
                cy.logout();
                cy.wait(2000);
            });
        });

        //Cancel a Software and License request - With Files
        it('Cancel a Software and License request', () => {
            let username = Cypress.env('requestor_username');
            let password = Cypress.env('requestor_password');
            cy.log('=====username : ' + username);
            cy.log('=====password : ' + password);

            cy.login(username, password);
            cy.visit('/');

            cy.contains('Start New +').click();
            cy.contains('Request Goods or Services');

            cy.runPrimaryBpmnFile(true);

            /*            cy.contains('Please select the type of request to start the process.');
                        // wait a second to ensure we can click the radio button
            
                        cy.wait(2000);
                        cy.get('input#root-procurement').click();
                        cy.wait(2000);
            
            
                        cy.get('button')
                            .contains(/^Submit$/)
                            .click();
            */

            cy.contains(
                'Request Goods or Services',
                { timeout: 60000 }
            );

            cy.url().then((currentUrl) => {
                // if url is "/tasks/8/d37c2f0f-016a-4066-b669-e0925b759560"
                // extract the digits after /tasks
                const processInstanceId = currentUrl.match(/(?<=\/tasks\/)\d+/)[0];
                cy.log('==###############===processInstanceId : ', processInstanceId);
                let projectId = Cypress.env('project_id');
                cy.wait(2000);
                cy.get('#root_project').select(projectId);
                cy.get('#root_category').select('soft_and_lic');
                cy.get('#root_purpose').clear().type('Sware\nA software license is a document that provides legally binding guidelines for the use and distribution of software.\nSoftware licenses typically provide end users with the right to one or more copies of the software without violating copyrights');
                cy.get('#root_criticality').select('High');
                cy.get('#root_period').clear().type('25-11-2025');
                cy.get('body').click();
                cy.get('#root_vendor').clear().type('Microsoft');
                cy.get('#root_payment_method').select('Reimbursement');
                /* cy.get('button')
                     .contains(/^Submit$/)
                     .click();
 
                 cy.contains('Task: Enter NDR Items', { timeout: 60000 });
 */
                //item 0
                cy.get('#root_item_0_sub_category').select('op_src');
                cy.get('#root_item_0_item_name').clear().type('Open source software is code that is designed to be publicly accessible anyone can see, modify, END');
                cy.get('#root_item_0_qty').clear().type('2');
                cy.get('#root_item_0_currency_type').select('Crypto');
                cy.get('#root_item_0_currency').select('SNT');
                cy.get('#root_item_0_unit_price').type('1915');


                cy.get('#root_item > div:nth-child(3) > p > button').click();

                //item 1
                cy.get('#root_item_1_sub_category').select('lic_and_sub');
                cy.get('#root_item_1_item_name').clear().type('A software license is a document that provides legally binding guidelines for the use and distri END');
                cy.get('#root_item_1_qty').clear().type('1');
                cy.get('#root_item_1_currency_type').select('Fiat');
                cy.get('#root_item_1_currency').select('AED');
                cy.get('#root_item_1_unit_price').type('4500');


                cy.get('button')
                    .contains(/^Submit$/)
                    .click();

                cy.contains(
                    'Review and provide any supporting information or files for your request.',
                    { timeout: 60000 }
                );

                cy.get('.cds--text-area__wrapper').find('#root').type('2021 Newest HP 17.3 inch FHD Laptop, AMD Ryzen 5 5500U 6core(Beat i7-1160G7, up to 4.0GHz),16GB RAM, 1TB PCIe SSD, Bluetooth 4.2, WiFi, HDMI, USB-A&C, Windows 10 S, w/Ghost Manta Accessories, Silver\nhttps://www.amazon.com/HP-i7-11G7-Bluetooth-Windows');


                cy.get('#root > div:nth-child(3) > p > button').click();

                cy.get("input[type=file]")
                    .attachFile(['lorem-ipsum.pdf']);
                cy.wait(1000);

                cy.get('#root > div:nth-child(3) > p > button').click();
                cy.wait(1000);

                cy.get('#root > div.row.array-item-list > div:nth-child(2) > div > div.cds--sm\\:col-span-1.cds--md\\:col-span-1.cds--lg\\:col-span-1.cds--css-grid-column > div > div > button.btn.btn-default.array-item-move-up > svg').click();
                cy.wait(1000);
                cy.get("input[type=file]")
                    .attachFile(['png-5mb-1.png']);
                cy.wait(1000);

                cy.get('#root > div:nth-child(3) > p > button').click();
                cy.wait(1000);

                cy.get('#root > div.row.array-item-list > div:nth-child(3) > div > div.cds--sm\\:col-span-1.cds--md\\:col-span-1.cds--lg\\:col-span-1.cds--css-grid-column > div > div > button.btn.btn-default.array-item-move-up > svg').click();
                cy.wait(1000);
                cy.get('#root > div.row.array-item-list > div:nth-child(2) > div > div.cds--sm\\:col-span-1.cds--md\\:col-span-1.cds--lg\\:col-span-1.cds--css-grid-column > div > div > button.btn.btn-default.array-item-move-up > svg').click();
                cy.wait(1000);

                cy.get("input[type=file]")
                    .attachFile(['Free_Test_Data_1MB_PDF.pdf']);
                cy.wait(1000);

                cy.get('#root > div:nth-child(3) > p > button').click();
                cy.wait(1000);

                cy.get('#root > div.row.array-item-list > div:nth-child(4) > div > div.cds--sm\\:col-span-1.cds--md\\:col-span-1.cds--lg\\:col-span-1.cds--css-grid-column > div > div > button.btn.btn-default.array-item-move-up > svg').click();
                cy.wait(1000);
                cy.get('#root > div.row.array-item-list > div:nth-child(3) > div > div.cds--sm\\:col-span-1.cds--md\\:col-span-1.cds--lg\\:col-span-1.cds--css-grid-column > div > div > button.btn.btn-default.array-item-move-up > svg').click();
                cy.wait(1000);
                cy.get('#root > div.row.array-item-list > div:nth-child(2) > div > div.cds--sm\\:col-span-1.cds--md\\:col-span-1.cds--lg\\:col-span-1.cds--css-grid-column > div > div > button.btn.btn-default.array-item-move-up > svg').click();
                cy.wait(1000);

                cy.get("input[type=file]")
                    .attachFile(['png-5mb-2.png']);

                cy.wait(2000);

                cy.contains('Cancel the Request').click();

                cy.get('input[value="Cancel the Request"]').click();

                cy.get('button')
                    .contains(/^Submit$/)
                    .click();

                cy.get('button')
                    .contains(/^Return to Home$/)
                    .click();

                cy.contains('Started by me', { timeout: 60000 });
                cy.logout();

            });
        });
    });
});

